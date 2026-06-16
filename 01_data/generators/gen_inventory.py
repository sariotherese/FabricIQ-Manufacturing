"""
Generate a synthetic finished-goods INVENTORY SNAPSHOT for the Betrimex Fabric demo.

Business use case
-----------------
Operations managers need to be **alerted before a Cocoxim SKU runs out of stock**
at a distribution center, so they can trigger a restock (production replenishment)
in time. This dataset answers: "Which products at which warehouse are at or below
their reorder point right now, and how much should we re-order?"

Why an inventory dataset (not shipments / orders)?
- `fact_sales_order_dim` tells us what shipped OUT (demand/issues).
- `fact_production_run_dim` tells us what was produced IN (supply/receipts).
- Neither alone gives **stock on hand**. Inventory = opening + receipts - issues,
  and the low-stock alert + reorder-point logic only works on that running balance.

How it's derived (grounded in the existing synthetic data)
----------------------------------------------------------
- Receipts  = production output, converted from `actual_yield` to consumer units.
- Issues    = `quantity_units` from sales orders.
- Daily receipts & issues are allocated across 3 finished-goods warehouses by a
  fixed share, then rolled forward day-by-day per (product, warehouse) to a
  closing on-hand balance.
- A reorder point (ROP = avg_daily_demand x lead_time + safety_stock) drives the
  `stock_status`, `restock_alert`, and `recommended_order_units`.

Proposed Gold table: `fact_inventory_snapshot_dim`
  Grain: one row per (snapshot_date, product, warehouse)

Inputs : 01_data/raw/production_runs.csv, 01_data/raw/sales_orders.csv
Outputs: 01_data/raw/inventory_snapshots.csv   (daily snapshot, the fact table)
         01_data/raw/inventory_alerts.csv       (latest-day low-stock alerts only)
"""

import math
import random
from pathlib import Path

import pandas as pd

# ---- Config ----
SEED = 42
TRAILING_DEMAND_DAYS = 28      # window for average daily demand
SAFETY_DAYS = 7                # safety stock expressed in days of demand
REVIEW_PERIOD_DAYS = 7         # how often we review/replenish
random.seed(SEED)

# ---- Paths ----
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR.parent / "raw"
RUNS_FILE = RAW_DIR / "production_runs.csv"
SALES_FILE = RAW_DIR / "sales_orders.csv"
OUTPUT_FILE = RAW_DIR / "inventory_snapshots.csv"
ALERTS_FILE = RAW_DIR / "inventory_alerts.csv"

for f in (RUNS_FILE, SALES_FILE):
    if not f.exists():
        raise FileNotFoundError(
            f"{f.name} not found in {RAW_DIR}. Run gen_production_runs.py and "
            "gen_sales_orders.py first."
        )

# ---- Finished-goods warehouses (distribution centers) ----
# share = portion of national receipts AND issues handled by the DC (kept equal on
# both sides so each DC's balance stays coherent). lead_time = replenishment days.
WAREHOUSES = {
    "HCMC Distribution Center": {"region": "Domestic South", "share": 0.45, "lead_time_days": 3},
    "Ha Noi Distribution Center": {"region": "Domestic North", "share": 0.25, "lead_time_days": 5},
    "Hai Phong Export Hub": {"region": "Export", "share": 0.30, "lead_time_days": 7},
}


def fill_size(product: str) -> float:
    """Liters (or kg) per consumer unit — converts bulk yield to sellable units."""
    if "330ml" in product:
        return 0.33
    if "1L" in product:
        return 1.0
    if "Coconut Milk" in product or "Coconut Cream" in product:
        return 0.40   # 400ml can
    if "Coconut Oil" in product:
        return 0.50   # 500ml / ~0.5kg bottle
    if "Desiccated" in product:
        return 0.25   # 250g pack
    return 1.0


def product_family(product: str) -> str:
    if "Coconut Water" in product:
        return "Coconut Water"
    if "Coconut Milk" in product:
        return "Coconut Milk"
    if "Coconut Cream" in product:
        return "Coconut Cream"
    if "Coconut Oil" in product:
        return "Coconut Oil"
    if "Desiccated" in product:
        return "Desiccated Coconut"
    return "Other"


def stock_status(on_hand: float, safety: float, reorder: float) -> str:
    if on_hand <= 0:
        return "OUT"
    if on_hand <= safety:
        return "CRITICAL"
    if on_hand <= reorder:
        return "LOW"
    return "OK"


# ---- Load inputs ----
print("Loading production runs and sales orders...")
runs = pd.read_csv(RUNS_FILE, parse_dates=["start_datetime"])
sales = pd.read_csv(SALES_FILE, parse_dates=["order_date"])

# Receipts: production output converted to consumer units, by product + date
runs = runs.assign(
    snapshot_date=runs["start_datetime"].dt.normalize(),
    units_produced=(runs["actual_yield"] / runs["product"].map(fill_size)).round().astype(int),
)
receipts = (
    runs.groupby(["product", "snapshot_date"])["units_produced"].sum().rename("receipts").reset_index()
)

# Issues: units shipped out, by product + date
sales = sales.assign(snapshot_date=sales["order_date"].dt.normalize())
issues = (
    sales.groupby(["product", "snapshot_date"])["quantity_units"].sum().rename("issues").reset_index()
)

# ---- Build the daily calendar and product list ----
all_dates = pd.concat([receipts["snapshot_date"], issues["snapshot_date"]])
date_index = pd.date_range(all_dates.min(), all_dates.max(), freq="D")
products = sorted(set(receipts["product"]) | set(issues["product"]))
print(f"Products: {len(products)} | Warehouses: {len(WAREHOUSES)} | Days: {len(date_index):,}")

# Pivot receipts/issues to product x date matrices for fast lookup
receipts_wide = (
    receipts.pivot(index="snapshot_date", columns="product", values="receipts")
    .reindex(date_index).fillna(0.0)
)
issues_wide = (
    issues.pivot(index="snapshot_date", columns="product", values="issues")
    .reindex(date_index).fillna(0.0)
)

# ---- Roll forward inventory per (product, warehouse) ----
print("Simulating daily inventory balances and reorder alerts...")
rows = []

for product in products:
    family = product_family(product)
    prod_issues = issues_wide.get(product, pd.Series(0.0, index=date_index))
    prod_receipts = receipts_wide.get(product, pd.Series(0.0, index=date_index))

    # Overall avg daily national demand for this product (warmup fallback)
    overall_daily = max(prod_issues.mean(), 1.0)

    for wh, cfg in WAREHOUSES.items():
        share = cfg["share"]
        lead_time = cfg["lead_time_days"]
        region = cfg["region"]

        wh_issues = (prod_issues * share).to_numpy()
        wh_receipts = (prod_receipts * share).to_numpy()

        # Seed opening stock at a healthy ~2x order-up-to level
        avg_daily = overall_daily * share
        safety = SAFETY_DAYS * avg_daily
        reorder = avg_daily * lead_time + safety
        order_up_to = reorder + REVIEW_PERIOD_DAYS * avg_daily
        on_hand = order_up_to * 2.0

        on_order = 0.0
        inbound = {}  # arrival_index -> qty
        recent_issues = []

        for i, day in enumerate(date_index):
            # 1. Receive any scheduled replenishment + same-day production receipts
            arrived = inbound.pop(i, 0.0)
            on_order -= arrived
            opening = on_hand
            day_receipts = wh_receipts[i] + arrived
            day_issues = wh_issues[i]

            # 2. Apply flows (clamp at 0 — a stockout means lost/backordered sales)
            on_hand = max(0.0, opening + day_receipts - day_issues)

            # 3. Trailing average daily demand
            recent_issues.append(wh_issues[i])
            if len(recent_issues) > TRAILING_DEMAND_DAYS:
                recent_issues.pop(0)
            avg_daily = max(sum(recent_issues) / len(recent_issues), overall_daily * share * 0.25)

            # 4. Reorder-point parameters
            safety = SAFETY_DAYS * avg_daily
            reorder = avg_daily * lead_time + safety
            order_up_to = reorder + REVIEW_PERIOD_DAYS * avg_daily

            status = stock_status(on_hand, safety, reorder)
            restock_alert = on_hand <= reorder

            # 5. Place a replenishment order if below ROP and nothing already inbound
            recommended = 0.0
            if restock_alert and on_order <= 0:
                recommended = max(0.0, order_up_to - (on_hand + on_order))
                if recommended > 0:
                    on_order += recommended
                    inbound[i + lead_time] = inbound.get(i + lead_time, 0.0) + recommended

            days_of_supply = round(on_hand / avg_daily, 1) if avg_daily > 0 else None

            rows.append({
                "snapshot_date": day.strftime("%Y-%m-%d"),
                "product": product,
                "product_family": family,
                "warehouse": wh,
                "region": region,
                "opening_units": int(round(opening)),
                "receipts_units": int(round(day_receipts)),
                "issues_units": int(round(day_issues)),
                "on_hand_units": int(round(on_hand)),
                "avg_daily_demand": round(avg_daily, 1),
                "lead_time_days": lead_time,
                "safety_stock_units": int(round(safety)),
                "reorder_point_units": int(round(reorder)),
                "on_order_units": int(round(on_order)),
                "days_of_supply": days_of_supply,
                "stock_status": status,
                "restock_alert": restock_alert,
                "recommended_order_units": int(round(recommended)),
            })

# ---- Write the snapshot fact ----
df = pd.DataFrame(rows)
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
print(f"\nWrote {len(df):,} inventory snapshots to {OUTPUT_FILE.name}")

# ---- Manager alert view: most recent day with outstanding restock alerts ----
# This is the "as of latest" alert inbox a manager would act on.
alerting = df.loc[df["restock_alert"], "snapshot_date"]
latest_date = alerting.max() if not alerting.empty else df["snapshot_date"].max()
alerts = (
    df[(df["snapshot_date"] == latest_date) & (df["restock_alert"])]
    .sort_values(["stock_status", "days_of_supply"])
    .reset_index(drop=True)
)
alert_cols = [
    "snapshot_date", "warehouse", "product", "product_family", "on_hand_units",
    "reorder_point_units", "days_of_supply", "stock_status", "recommended_order_units",
]
alerts[alert_cols].to_csv(ALERTS_FILE, index=False, encoding="utf-8")
print(f"Wrote {len(alerts):,} active restock alerts ({latest_date}) to {ALERTS_FILE.name}")

# ---- Console summary ----
print("\nStock status distribution (all snapshots):")
print(df["stock_status"].value_counts())

print(f"\n=== RESTOCK ALERTS for {latest_date} (top 15 by urgency) ===")
if alerts.empty:
    print("No SKUs at or below reorder point. All stock healthy.")
else:
    print(alerts[alert_cols].head(15).to_string(index=False))
