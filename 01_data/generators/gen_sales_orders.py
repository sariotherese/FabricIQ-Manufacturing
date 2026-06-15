"""
Generate synthetic sales orders for the Betrimex Fabric demo.

Each order is tied to one or more production runs (linking what was sold
back to which Cocoxim batch). Mix of domestic Vietnamese retail/HORECA
and exports to 40+ countries. Organic orders only fulfill from organic
production runs — enables lot-level traceability for EU/USDA audits.

Output: 01_data/raw/sales_orders.csv  (~80,000 rows)
"""

import random
from datetime import timedelta
from pathlib import Path
import pandas as pd
from faker import Faker

# ---- Config ----
NUM_ORDERS = 80_000
SEED = 42

# ---- Paths ----
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR.parent / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
RUNS_FILE = RAW_DIR / "production_runs.csv"
OUTPUT_FILE = RAW_DIR / "sales_orders.csv"

if not RUNS_FILE.exists():
    raise FileNotFoundError(
        "production_runs.csv not found. Run gen_production_runs.py first."
    )

random.seed(SEED)
Faker.seed(SEED)
faker = Faker()

# ---- Load runs ----
runs_df = pd.read_csv(RUNS_FILE, parse_dates=["start_datetime"])
print(f"Loaded {len(runs_df):,} runs")

# Pre-split organic vs conventional run pools
organic_runs = runs_df[runs_df["is_organic_run"] == True].reset_index(drop=True)
conv_runs = runs_df[runs_df["is_organic_run"] == False].reset_index(drop=True)

# ---- Reference data ----
EXPORT_COUNTRIES = {
    "United States":  {"region": "North America", "currency": "USD", "fx_to_usd": 1.00},
    "Canada":         {"region": "North America", "currency": "USD", "fx_to_usd": 1.00},
    "Germany":        {"region": "Europe",        "currency": "EUR", "fx_to_usd": 1.08},
    "Netherlands":    {"region": "Europe",        "currency": "EUR", "fx_to_usd": 1.08},
    "France":         {"region": "Europe",        "currency": "EUR", "fx_to_usd": 1.08},
    "United Kingdom": {"region": "Europe",        "currency": "USD", "fx_to_usd": 1.00},
    "Japan":          {"region": "Asia-Pacific",  "currency": "USD", "fx_to_usd": 1.00},
    "South Korea":    {"region": "Asia-Pacific",  "currency": "USD", "fx_to_usd": 1.00},
    "Australia":      {"region": "Asia-Pacific",  "currency": "USD", "fx_to_usd": 1.00},
    "Singapore":      {"region": "Asia-Pacific",  "currency": "USD", "fx_to_usd": 1.00},
    "Malaysia":       {"region": "Asia-Pacific",  "currency": "USD", "fx_to_usd": 1.00},
    "Philippines":    {"region": "Asia-Pacific",  "currency": "USD", "fx_to_usd": 1.00},
    "China":          {"region": "Asia-Pacific",  "currency": "USD", "fx_to_usd": 1.00},
    "UAE":            {"region": "Middle East",   "currency": "USD", "fx_to_usd": 1.00},
    "Saudi Arabia":   {"region": "Middle East",   "currency": "USD", "fx_to_usd": 1.00},
}

DOMESTIC_CHANNELS = ["Modern Trade", "General Trade", "HORECA", "E-commerce", "Convenience"]
EXPORT_CHANNELS = ["Retail Distributor", "Wholesale", "Private Label", "Foodservice"]

# Customers
DOMESTIC_CUSTOMERS = [
    "WinMart", "Co.opmart", "Bach Hoa Xanh", "VinMart+", "MM Mega Market",
    "Aeon Vietnam", "GS25 Vietnam", "Family Mart", "Circle K Vietnam",
    "Lotte Mart", "BRG Mart", "GO! Big C", "Saigon Co.op", "Annam Gourmet",
]

# Per-unit price in USD (FOB) by product family
def base_price_usd(product: str) -> float:
    if "Organic" in product:
        if "1L" in product:        return 1.35
        if "330ml" in product:     return 0.55
        return 1.20
    if "Coconut Water" in product:
        if "1L" in product:        return 0.95
        if "330ml" in product:     return 0.38
    if "Coconut Milk" in product:  return 1.10
    if "Coconut Cream" in product: return 1.30
    if "Coconut Oil" in product:   return 4.20
    if "Desiccated" in product:    return 2.80
    return 1.00

# ---- Generate ----
print(f"Generating {NUM_ORDERS:,} sales orders...")
rows = []

domestic_share = 0.55  # 55% domestic Vietnam, 45% export
organic_share_export = 0.35  # organic over-indexes in export

for i in range(NUM_ORDERS):
    is_domestic = random.random() < domestic_share

    # Organic preference for export
    want_organic = (not is_domestic) and (random.random() < organic_share_export)
    pool = organic_runs if want_organic else conv_runs
    if pool.empty:
        pool = runs_df

    run = pool.sample(1).iloc[0]
    product = run["product"]
    is_organic_product = "Organic" in product

    # Order date = run end + 1–60 days shipping lag
    run_date = run["start_datetime"]
    order_date = run_date + timedelta(days=random.randint(1, 60))

    # Customer + country
    if is_domestic:
        country = "Vietnam"
        region = "Domestic"
        channel = random.choice(DOMESTIC_CHANNELS)
        customer = random.choice(DOMESTIC_CUSTOMERS)
        currency = "VND"
        fx = 24500  # USD to VND
    else:
        country, info = random.choice(list(EXPORT_COUNTRIES.items()))
        region = info["region"]
        channel = random.choice(EXPORT_CHANNELS)
        customer = faker.company()
        currency = info["currency"]
        fx = info["fx_to_usd"]

    # Quantity — bigger for export wholesale, smaller for retail
    if channel in ("Wholesale", "Private Label"):
        qty_units = random.randint(20_000, 200_000)
    elif channel in ("Modern Trade", "Retail Distributor"):
        qty_units = random.randint(2_000, 50_000)
    else:
        qty_units = random.randint(500, 10_000)

    # Pricing
    unit_price_usd = base_price_usd(product)
    # Small variance + organic premium already baked in
    unit_price_usd *= random.uniform(0.92, 1.08)
    revenue_usd = unit_price_usd * qty_units
    if currency == "VND":
        revenue_local = revenue_usd * fx
    else:
        revenue_local = revenue_usd * fx

    # Margin — organic is higher margin
    margin_pct = random.normalvariate(0.28 if is_organic_product else 0.20, 0.04)
    margin_pct = max(0.05, min(margin_pct, 0.45))
    margin_usd = revenue_usd * margin_pct

    # On-time delivery rate — 92% in general, 88% for organic certs
    on_time = random.random() < (0.88 if is_organic_product else 0.92)

    rows.append({
        "order_id":         f"SO-{i + 1:07d}",
        "order_date":       order_date.strftime("%Y-%m-%d"),
        "customer":         customer,
        "country":          country,
        "region":           region,
        "channel":          channel,
        "is_domestic":      is_domestic,
        "is_organic":       is_organic_product,
        "run_id":           run["run_id"],
        "product":          product,
        "quantity_units":   qty_units,
        "unit_price_usd":   round(unit_price_usd, 3),
        "revenue_usd":      round(revenue_usd, 2),
        "revenue_local":    round(revenue_local, 2),
        "currency":         currency,
        "margin_pct":       round(margin_pct * 100, 2),
        "margin_usd":       round(margin_usd, 2),
        "on_time_delivery": on_time,
    })

    if (i + 1) % 10_000 == 0:
        print(f"  {i + 1:,} / {NUM_ORDERS:,}")

# ---- Write ----
df = pd.DataFrame(rows)
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print(f"\nWrote {len(df):,} sales orders to {OUTPUT_FILE.name}")
print("\nDomestic vs Export:")
print(df["is_domestic"].value_counts(normalize=True).round(3))
print("\nTop 10 export markets by revenue (USD):")
print(
    df[~df["is_domestic"]]
    .groupby("country")["revenue_usd"]
    .sum().sort_values(ascending=False).head(10).round(0)
)
print("\nRevenue by channel (USD):")
print(df.groupby("channel")["revenue_usd"].sum().sort_values(ascending=False).round(0))
print("\nOrganic share of revenue:")
print(df.groupby("is_organic")["revenue_usd"].sum().round(0))