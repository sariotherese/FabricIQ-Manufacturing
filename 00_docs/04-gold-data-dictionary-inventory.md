# Betrimex Fabric Demo — Gold Layer Data Dictionary (Inventory)

**Version:** 1.0
**Source layer:** Gold (derived inventory snapshot built from `fact_production_run_dim` receipts and `fact_sales_order_dim` issues; generator: `01_data/generators/gen_inventory.py`)
**Lakehouse:** `agri_lakehouse`  **Schema:** `golddb`
**Table naming:** `<entity>_dim` (the `_dim` suffix is the storage convention for every Gold Delta table — it does **not** imply the table is a dimension)
**Owner:** Therese Sario, Microsoft Philippines
**Customer:** Betrimex (Ben Tre Trading & Import-Export JSC) — Vietnamese coconut processor, brand Cocoxim

---

## Business Use Case

Operations managers must be **alerted before a Cocoxim SKU runs out of stock** at a distribution center, so they can trigger a production replenishment in time. This dataset answers: *"Which products at which warehouse are at or below their reorder point right now, and how much should we re-order?"*

A shipment or order dataset only captures one side of the flow. Stock on hand — and therefore the low-stock alert — requires a running balance:

```
on_hand = opening + receipts (production output) − issues (sales shipments)
restock_alert = on_hand ≤ reorder_point
reorder_point = avg_daily_demand × lead_time_days + safety_stock
```

---

## Star Schema Position

```
   fact_production_run_dim ─┐  (receipts = actual_yield → units)
                            ├──▶ fact_inventory_snapshot_dim ──▶ inventory_alert_dim
   fact_sales_order_dim ────┘  (issues = quantity_units)             (manager view)
                                          │
                       product_dim · date_dim  (conform on product / snapshot_date)
```

- `fact_inventory_snapshot_dim` is the daily stock-position fact.
- `inventory_alert_dim` is the manager-facing alert view: the latest snapshot filtered to items needing a restock.
- Both conform to `product_dim` (on `product`) and `date_dim` (on `snapshot_date`).

---

## Table Index

| # | Gold table (golddb) | Role | Grain | Primary key |
|---|---|---|---|---|
| 1 | `fact_inventory_snapshot_dim` | Fact | One row per snapshot date + product + warehouse | `inventory_key` (surrogate; natural key = `snapshot_date` + `product` + `warehouse`) |
| 2 | `inventory_alert_dim` | Fact (view) | One row per alerting product + warehouse on the latest snapshot | `inventory_key` (FK → `fact_inventory_snapshot_dim`) |

> Source files: `01_data/raw/inventory_snapshots.csv` (full daily history) and `01_data/raw/inventory_alerts.csv` (latest-day restock alerts only).

---

## 1. `fact_inventory_snapshot_dim` — Daily Finished-Goods Inventory

**Grain:** One row per (`snapshot_date`, `product`, `warehouse`).  **Key:** `inventory_key` (surrogate)

**Business context:** The daily stock position of every Cocoxim SKU at every distribution center — the running balance of what was on hand, what came in from production, and what shipped out. It is the single source for stock visibility, days-of-supply, reorder-point alerting, and restock recommendations.

| Column | Type | Nullable | Description | Business context | Notes |
|---|---|---|---|---|---|
| `inventory_key` | String | No | Surrogate primary key for the stock position | The stable single-column identifier for one SKU-warehouse-day balance; lets the alert table reference a snapshot with one key. | SHA-256 of `snapshot_date`‖`warehouse`‖`product`. |
| `snapshot_date` | Date | No | The day the stock position is measured | Puts every balance on a daily time axis for trend and as-of reporting. | FK → `date_dim.date`. |
| `product` | String | No | Cocoxim SKU | The item being stocked and replenished. | FK → `product_dim.product`. |
| `product_family` | String | No | Product category | Rolls SKUs up for category-level stock and service reporting. | e.g. `Coconut Water`, `Coconut Milk`. |
| `warehouse` | String | No | Distribution center holding the stock | Localizes stock and alerts to the site that must act. | One of HCMC, Ha Noi, Hai Phong Export Hub. |
| `region` | String | No | Region served by the warehouse | Groups DCs for regional availability analysis. | `Domestic South`, `Domestic North`, `Export`. |
| `opening_units` | Integer | No | On-hand units at the start of the day | The carry-in balance before the day's flows. | Measure. |
| `receipts_units` | Integer | No | Units received that day | Inbound supply from production + scheduled replenishment arrivals. | Derived from `actual_yield` converted to consumer units. |
| `issues_units` | Integer | No | Units shipped out that day | Demand fulfilled — the draw-down on stock. | Derived from sales `quantity_units`. |
| `on_hand_units` | Integer | No | Closing on-hand units | The current stock level — the number the alert is judged against. | `max(0, opening + receipts − issues)`. |
| `avg_daily_demand` | Float | No | Trailing average daily demand | The demand rate driving reorder point and days-of-supply. | 28-day trailing average. |
| `lead_time_days` | Integer | No | Replenishment lead time for the warehouse | How long restock takes — sets how early to reorder. | 3–7 days by DC. |
| `safety_stock_units` | Integer | No | Buffer stock to absorb demand variability | Protects against stockouts during the lead time. | `safety_days × avg_daily_demand`. |
| `reorder_point_units` | Integer | No | Stock level that triggers a restock | The threshold the alert fires at — the core rule. | `avg_daily_demand × lead_time + safety_stock`. |
| `on_order_units` | Integer | No | Units already on order (in transit) | Prevents duplicate ordering while a replenishment is inbound. | Measure. |
| `days_of_supply` | Float | Yes | Days of stock left at current demand | The headline urgency metric managers watch. | `on_hand ÷ avg_daily_demand`; null if no demand. |
| `stock_status` | String | No | Health classification of the stock level | One-glance status for dashboards and triage. | `OK`, `LOW`, `CRITICAL`, `OUT`. |
| `restock_alert` | Boolean | No | Whether stock is at/below reorder point | The flag that drives the manager alert. | True when `on_hand ≤ reorder_point`. |
| `recommended_order_units` | Integer | No | Suggested replenishment quantity | Tells the manager how much to order to reach the target level. | `order_up_to − (on_hand + on_order)`; 0 if not alerting. |

---

## 2. `inventory_alert_dim` — Restock Alert View

**Grain:** One row per alerting (`product`, `warehouse`) on the latest snapshot.  **Key:** `inventory_key` (FK → `fact_inventory_snapshot_dim`)

**Business context:** The manager's action list — the latest snapshot filtered to only SKUs at or below their reorder point, sorted by urgency. This is what gets surfaced as the "restock now" alert and feeds the replenishment decision.

| Column | Type | Nullable | Description | Business context | Notes |
|---|---|---|---|---|---|
| `inventory_key` | String | No | Foreign key to the originating stock position | Ties each alert to its exact `fact_inventory_snapshot_dim` row with a single key. | SHA-256 of `snapshot_date`‖`warehouse`‖`product`; matches the snapshot. |
| `snapshot_date` | Date | No | The day the alert was raised | Establishes the "as of" date of the alert inbox. | Latest snapshot with outstanding alerts. |
| `warehouse` | String | No | Distribution center needing the restock | Directs the alert to the responsible site. | |
| `product` | String | No | Cocoxim SKU at risk of stockout | Identifies exactly what to replenish. | FK → `product_dim.product`. |
| `product_family` | String | No | Product category | Lets managers prioritize by category. | |
| `on_hand_units` | Integer | No | Current on-hand units | Shows how little stock remains. | |
| `reorder_point_units` | Integer | No | Reorder threshold that was breached | Explains why the alert fired. | |
| `days_of_supply` | Float | Yes | Days of stock left at current demand | The urgency ranking for the alert. | Lower = more urgent. |
| `stock_status` | String | No | Health classification | Severity label (`LOW` / `CRITICAL` / `OUT`). | |
| `recommended_order_units` | Integer | No | Suggested replenishment quantity | The recommended action — how much to order. | |
