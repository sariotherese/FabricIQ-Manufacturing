# Data Source Instructions — Contoso Manufacturing Company Gold Star Schema

**Schema:** `agri_lakehouse.golddb`

## How the Tables Connect

**Star pattern:** 4 facts radiate from `date_dim` and product/process dimensions:
- `fact_intake_dim` ← `date_dim`, `farmer_dim` (raw supply)
- `fact_production_run_dim` ← `date_dim`, `plant_dim`, `product_dim` (production efficiency)
- `fact_quality_test_dim` ← `date_dim`, `run_id` (FK to production run), `test_type_dim` (QA specs)
- `fact_sales_order_dim` ← `date_dim`, `run_id` (FK to production run), `customer_dim` (revenue)
- `bridge_lot_run_dim` ← `run_id`, `lot_id` (many-to-many; enables traceability farmer → product)
- `fact_inventory_snapshot_dim` ← `date_dim`, `product_dim` (daily stock per SKU per DC)
- `inventory_alert_dim` ← `inventory_key` (FK to inventory snapshot; manager restock list)

## Querying Tips

**Traceability (order → farmers):** Start with `fact_sales_order_dim` on order_id → join `fact_production_run_dim` on run_id → join `bridge_lot_run_dim` on run_id → join `fact_intake_dim` on lot_id → join `farmer_dim` on farmer_key.

**Yield investigation:** Query `fact_production_run_dim` for date/plant/line → check `yield_pct`, `avg_brix`, `grade_a_pct`, `downtime_minutes` → join `fact_quality_test_dim` on run_id for failures → drill to source lots via bridge/intake.

**Inventory alerts:** Query `inventory_alert_dim` (latest day only) to see what needs reordering now, sorted by `days_of_supply` (ascending = most urgent).

**Revenue & margin:** Use `fact_sales_order_dim` grouped by `customer_key`, `product_key`, or date range; join `customer_dim` for region/channel breakdown.

**Quality trends:** Aggregate `fact_quality_test_dim` by `test_name`, `category`, or date; join `test_type_dim` for spec target/tolerance context.

**Supply trends:** Use `fact_intake_dim` grouped by `district`, `grade`, date range; join `farmer_dim` for organic flag and farmer attributes.

## Data Quality Notes

- **Date joins:** Use `date_key` (yyyyMMdd int) not date strings; join to `date_dim` for year/quarter/month attributes
- **Surrogate keys:** `product_key`, `plant_key`, `customer_key`, `test_type_key` are deterministic SHA-256 hashes — stable across reloads
- **Nulls:** `days_of_supply` null if no demand history; never join on null dates or missing keys
- **Referential integrity:** Every fact row references valid dimension keys; use INNER JOINs by default
- **Organic segregation:** Some runs/lots are organic-certified; check `is_organic` flags for compliance filtering
- **Inventory:** `fact_inventory_snapshot_dim` is daily (one row per product per warehouse per day); `inventory_alert_dim` is a filtered view of latest day only

