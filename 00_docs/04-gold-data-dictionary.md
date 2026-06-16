# Betrimex Fabric Demo — Gold Layer Data Dictionary

**Version:** 1.0
**Source layer:** Gold (star schema produced by `02_notebooks/03_gold_curate.ipynb`)
**Lakehouse:** `agri_lakehouse`  **Schema:** `golddb`
**Table naming:** `<entity>_dim` (the `_dim` suffix is the storage convention for every Gold Delta table — it does **not** imply the table is a dimension)
**Owner:** Therese Sario, Microsoft Philippines
**Customer:** Betrimex (Ben Tre Trading & Import-Export JSC) — Vietnamese coconut processor, brand Cocoxim

---

## Star Schema Overview

```
                        date_dim
                           │
        farmer_dim ── fact_intake_dim ──┐
              │                          │
   bridge_lot_run_dim                    │
              │                          │
        fact_production_run_dim ── plant_dim
              │   │   │
              │   │   └── product_dim
              │   │
              │   ├── fact_quality_test_dim ── test_type_dim
              │   │
              │   └── fact_sales_order_dim ── customer_dim
```

**Grain & role summary**

- Dimensions provide descriptive context and surrogate keys.
- Facts hold the measurable events (intake, runs, tests, orders).
- `bridge_lot_run_dim` resolves the many-to-many between lots and runs and carries `farmer_key` for fast lot-level traceability.

---

## Table Index

| # | Gold table (golddb) | Role | Grain | Primary / surrogate key |
|---|---|---|---|---|
| 1 | `farmer_dim` | Dimension | One row per farmer | `farmer_key` |
| 2 | `product_dim` | Dimension | One row per SKU | `product_key` |
| 3 | `plant_dim` | Dimension | One row per plant + line | `plant_key` |
| 4 | `customer_dim` | Dimension | One row per customer + country + channel | `customer_key` |
| 5 | `date_dim` | Dimension | One row per calendar day | `date_key` |
| 6 | `test_type_dim` | Dimension | One row per QA test type | `test_type_key` |
| 7 | `fact_intake_dim` | Fact | One row per coconut lot | `lot_id` |
| 8 | `fact_production_run_dim` | Fact | One row per production run | `run_id` |
| 9 | `fact_quality_test_dim` | Fact | One row per QA test | `test_id` |
| 10 | `fact_sales_order_dim` | Fact | One row per sales order | `order_id` |
| 11 | `bridge_lot_run_dim` | Bridge | One row per (run, lot) pair | (`run_id`, `lot_id`) |

> Surrogate keys (`product_key`, `plant_key`, `customer_key`, `test_type_key`) are deterministic SHA-256 hashes of the business attributes, so they are stable across reloads.

---

## 1. `farmer_dim` — Farmer Dimension

**Grain:** One row per farmer.  **Key:** `farmer_key` (= `farmer_id`)

**Business context:** The master list of the smallholder coconut farmers who supply Betrimex across the Mekong Delta. It anchors supplier analytics and is the endpoint of every traceability query — answering "which farms did this product come from?" and "how much of our supply is organic-certified?"

| Column | Type | Nullable | Description | Business context | Notes |
|---|---|---|---|---|---|
| `farmer_key` | Integer | No | Surrogate key | Stable identifier used to link a farmer to their deliveries and to finished product. | Equal to `farmer_id`. Referenced by `fact_intake_dim` and `bridge_lot_run_dim`. |
| `farmer_id` | Integer | No | Natural farmer identifier | The supplier's ID in source systems, used when reconciling with field/procurement records. | From Silver. |
| `name` | String | No | Farmer's full name (Vietnamese) | Identifies the individual grower for audits, payments, and farmer engagement. | Diacritics preserved (UTF-8). |
| `district` | String | No | Mekong Delta province | Shows where supply originates, supporting regional sourcing strategy and risk concentration. | One of `Ben Tre`, `Tra Vinh`, `Tien Giang`, `Vinh Long`. |
| `province` | String | No | Province label | Province-level grouping for geographic supply reporting. | Currently equal to `district`. |
| `organic_certification` | String | No | Organic certification label | Confirms a farm's certification status — the basis for organic sourcing and premium pricing. | e.g. `Certified Organic`, `Non-Organic`. |
| `is_organic` | Boolean | No | Organic-certified flag | Fast filter to size organic vs. conventional supply for EU/USDA audit scope. | Derived in Silver. |

---

## 2. `product_dim` — Product Dimension

**Grain:** One row per SKU.  **Key:** `product_key` (SHA-256 of `product`)

**Business context:** The catalog of Cocoxim finished-goods SKUs. It lets the business slice production and sales by product and by product family, and distinguish organic from conventional lines.

| Column | Type | Nullable | Description | Business context | Notes |
|---|---|---|---|---|---|
| `product_key` | String | No | Surrogate key | Stable identifier linking a SKU to its production runs and sales orders. | SHA-256 hash of `product`. |
| `product` | String | No | Cocoxim SKU name | The branded product as customers order it — the level at which pricing and demand are managed. | e.g. `Cocoxim Coconut Water Original 330ml`. |
| `product_family` | String | No | Derived product family | Rolls SKUs into categories for portfolio-level revenue and yield comparison. | One of `Coconut Water`, `Coconut Milk`, `Coconut Cream`, `Coconut Oil`, `Desiccated Coconut`, `Other`. |
| `is_organic` | Boolean | No | Organic SKU flag | Separates the premium organic range from conventional for margin and compliance analysis. | From `is_organic_run`. |

---

## 3. `plant_dim` — Plant Dimension

**Grain:** One row per plant + line.  **Key:** `plant_key` (SHA-256 of `plant` + `line`)

**Business context:** The manufacturing footprint — each processing plant and the lines within it. It enables plant- and line-level performance benchmarking (yield, throughput, downtime) and separates organic-certified facilities from conventional ones.

| Column | Type | Nullable | Description | Business context | Notes |
|---|---|---|---|---|---|
| `plant_key` | String | No | Surrogate key | Stable identifier linking a specific line to its production runs. | SHA-256 hash of `plant` + `line`. |
| `plant` | String | No | Manufacturing plant | The site responsible for output — the unit for capacity and plant-vs-plant comparison. | e.g. `Ben Tre Main Plant`. |
| `line` | String | No | Production line within the plant | The specific line, used to pinpoint where yield or quality issues arise. | e.g. `Line 1`. |
| `plant_type` | String | No | Derived plant classification | Flags organic-dedicated facilities, which matters for certification segregation. | `Organic` if plant name contains "Organic", else `Conventional`. |

---

## 4. `customer_dim` — Customer Dimension

**Grain:** One row per customer + country + channel.  **Key:** `customer_key` (SHA-256 of `customer` + `country` + `channel`)

**Business context:** Who Betrimex sells to — domestic distributors and international export buyers. It underpins market analysis: revenue by country, region, and channel, and the domestic-vs-export split that drives commercial strategy.

| Column | Type | Nullable | Description | Business context | Notes |
|---|---|---|---|---|---|
| `customer_key` | String | No | Surrogate key | Stable identifier linking a customer to their orders. | SHA-256 hash of `customer` + `country` + `channel`. |
| `customer` | String | No | Customer name | The account being sold to — the level for relationship and account management. | Domestic distributors and export buyers. |
| `country` | String | No | Customer country | Destination market, key for export reporting and trade/tariff analysis. | |
| `region` | String | No | Sales region | Groups markets for territory-level sales performance. | |
| `channel` | String | No | Sales channel | Route to market, used to compare domestic, export, and retail economics. | e.g. `Domestic`, `Export`, `Retail`. |
| `is_domestic` | Boolean | No | Domestic vs. export flag | The headline split between home-market and export revenue. | |

---

## 5. `date_dim` — Date Dimension

**Grain:** One row per calendar day spanning all event dates.  **Key:** `date_key` (`yyyyMMdd` integer)

**Business context:** The shared calendar that ties intake, production, quality, and sales to a common time axis. It powers all trend, seasonality, and period-over-period reporting (harvest seasons, monthly yield, quarterly revenue).

| Column | Type | Nullable | Description | Business context | Notes |
|---|---|---|---|---|---|
| `date_key` | Integer | No | Surrogate key | The join key every fact uses to report "by date". | `yyyyMMdd` (e.g. `20250814`). |
| `date` | Date | No | Calendar date | The actual day an event occurred. | |
| `year` | Integer | No | Calendar year | Year-over-year comparison of supply, output, and sales. | |
| `quarter` | String | No | Quarter label | Quarterly business reviews and targets. | e.g. `Q3`. |
| `month` | Integer | No | Month number (1–12) | Monthly trending and ordering of periods. | |
| `month_name` | String | No | Full month name | Readable month labels for reports and dashboards. | e.g. `August`. |
| `day` | Integer | No | Day of month | Daily granularity for operational analysis. | |
| `day_of_week` | String | No | Weekday name | Reveals weekday vs. weekend operating patterns. | e.g. `Thursday`. |
| `week_of_year` | Integer | No | ISO week number | Weekly operational and supply cadence. | |
| `is_weekend` | Boolean | No | Weekend flag | Separates weekend operations, which affect shift staffing and throughput. | True for Saturday/Sunday. |

---

## 6. `test_type_dim` — QA Test Type Dimension

**Grain:** One row per QA test type.  **Key:** `test_type_key` (SHA-256 of `test_name`)

**Business context:** The catalog of quality-assurance checks Betrimex runs and the specifications each must meet. It defines what "in-spec" means and lets quality results be grouped by test category for food-safety and compliance reporting.

| Column | Type | Nullable | Description | Business context | Notes |
|---|---|---|---|---|---|
| `test_type_key` | String | No | Surrogate key | Stable identifier linking a test definition to its results. | SHA-256 hash of `test_name`. |
| `test_name` | String | No | QA test name | The specific check performed, e.g. sweetness or bacterial load. | e.g. `Brix`, `pH`, `Total Plate Count`. |
| `category` | String | No | Test category | Groups tests for category-level pass/fail rollups (esp. food safety). | `Chemical`, `Microbiological`, `Physical`. |
| `target` | Float | No | Target spec value | The ideal result the product should hit. | |
| `tolerance` | Float | No | Acceptable +/- variance from target | Defines the pass/fail window around target. | |
| `unit` | String | No | Measurement unit | Makes results interpretable and comparable to spec. | e.g. `°Bx`, `pH`, `CFU/mL`. |

---

## 7. `fact_intake_dim` — Coconut Intake Fact

**Grain:** One row per coconut lot.  **Key:** `lot_id`

**Business context:** Every batch of coconuts received from a farmer at a collection point — the raw-material supply that feeds production. It measures how much is coming in, at what quality, and from where, and is the starting point for supply traceability.

| Column | Type | Nullable | Description | Business context | Notes |
|---|---|---|---|---|---|
| `lot_id` | String | No | Lot identifier | The traceable unit of incoming supply, referenced all the way to finished product. | Degenerate dimension. |
| `farmer_key` | Integer | No | FK → `farmer_dim.farmer_key` | Ties each delivery to the farm that supplied it. | |
| `date_key` | Integer | No | FK → `date_dim.date_key` | Enables intake volume and quality trends over time (harvest seasons). | Derived from `intake_date`. |
| `intake_date` | Date | No | Date the lot was received | When supply arrived — used for freshness and seasonality analysis. | |
| `collection_point` | String | No | Betrimex hub of delivery | Identifies the receiving hub for logistics and regional intake reporting. | |
| `district` | String | No | Province the lot came from | Geographic origin of supply for sourcing and risk analysis. | |
| `weight_kg` | Float | No | Net weight of the lot | The core supply-volume measure (tonnes of coconut received). | Measure. |
| `brix` | Float | No | Sugar content of coconut water | Key quality measure that drives downstream processing yield. | Measure / quality driver. |
| `grade` | String | No | Quality grade | Intake quality classification used for pricing and sorting. | `A`, `B`, `C`. |
| `is_organic` | Boolean | No | Organic lot flag | Identifies certified-organic supply for segregation and audits. | |
| `quality_flag` | String | No | Derived quality flag | Quick at-a-glance status to spot problem lots (low sweetness/grade). | `Low Brix`, `Low Grade`, or `OK`. |

---

## 8. `fact_production_run_dim` — Production Run Fact

**Grain:** One row per production run.  **Key:** `run_id`

**Business context:** Each batch processed on a plant line — the heart of manufacturing performance. It links raw input to finished output and carries the headline efficiency KPI (yield %), along with the quality and downtime signals that explain why yield moves.

| Column | Type | Nullable | Description | Business context | Notes |
|---|---|---|---|---|---|
| `run_id` | String | No | Run identifier | The unit of production, linking inputs (lots) to outputs (product) and tests. | Degenerate dimension. |
| `date_key` | Integer | No | FK → `date_dim.date_key` | Enables production and yield trending over time. | Derived from `run_date`. |
| `product_key` | String | No | FK → `product_dim.product_key` | Ties output to the SKU being made. | |
| `plant_key` | String | No | FK → `plant_dim.plant_key` | Attributes performance to a specific plant and line. | |
| `plant` | String | No | Plant name | Where the batch ran — for plant-level benchmarking. | Denormalized. |
| `line` | String | No | Production line | Pinpoints the line for performance and troubleshooting. | Denormalized. |
| `product` | String | No | SKU produced | What was made in the run. | Denormalized. |
| `shift` | String | No | Production shift | Compares performance across shifts (staffing/operating patterns). | `Morning`, `Afternoon`, `Night`. |
| `start_datetime` | Timestamp | No | Run start | Marks when processing began, for scheduling and duration analysis. | |
| `end_datetime` | Timestamp | No | Run end | Marks completion, for throughput and turnaround analysis. | |
| `duration_hours` | Float | No | Run duration | How long the batch took — a throughput/efficiency measure. | Measure. |
| `input_weight_kg` | Float | No | Total raw coconut input | Raw material consumed — the denominator behind conversion efficiency. | Measure. |
| `expected_yield` | Float | No | Theoretical output | The target output given input and recipe — the yield benchmark. | Measure. |
| `actual_yield` | Float | No | Real measured output | What was actually produced — the basis for efficiency and loss. | Measure. |
| `yield_pct` | Float | No | actual / expected × 100 | **The headline manufacturing KPI** — how efficiently coconuts convert to product. | Recomputed defensively in Silver. |
| `yield_loss` | Float | No | `expected_yield − actual_yield` | Quantifies lost output — the gap to target in absolute terms. | Derived measure. |
| `yield_band` | String | No | Yield band | Buckets runs into performance tiers for quick exception spotting. | `High (>=90%)`, `Normal (80-90%)`, `Low (<80%)`. |
| `avg_brix` | Float | No | Weighted average brix of consumed lots | Input-quality signal — a leading explanation for yield variance. | Quality input signal. |
| `grade_a_pct` | Float | No | % of consumed lots that were Grade A | Input-quality signal — higher Grade A typically lifts yield. | Quality input signal. |
| `downtime_minutes` | Integer | No | Total downtime during the run | Lost operating time — a key driver of throughput and OEE. | Measure. |
| `is_organic_run` | Boolean | No | Organic SKU run flag | Flags organic production for certification and segregation. | |
| `num_lots_consumed` | Integer | No | Distinct lots used in the run | Indicates supply blending and the breadth of traceability per run. | |

---

## 9. `fact_quality_test_dim` — Quality Test Fact

**Grain:** One row per QA test.  **Key:** `test_id`

**Business context:** The food-safety and quality record — every lab/line test performed on a production run. It evidences that product met specification, supports pass/fail reporting, and is central to compliance and customer assurance.

| Column | Type | Nullable | Description | Business context | Notes |
|---|---|---|---|---|---|
| `test_id` | String | No | Test identifier | The unique record of a single quality check, for audit trails. | Degenerate dimension. |
| `run_id` | String | No | FK → `fact_production_run_dim.run_id` | Ties each test to the batch it certifies. | |
| `test_type_key` | String | No | FK → `test_type_dim.test_type_key` | Links the result to its spec definition and category. | |
| `date_key` | Integer | No | FK → `date_dim.date_key` | Enables quality trend and pass-rate analysis over time. | Derived from `test_date`. |
| `test_name` | String | No | QA test name | The check performed (e.g. sweetness, bacterial load). | Denormalized. |
| `category` | String | No | Test category | Groups results for category-level food-safety rollups. | Denormalized. |
| `value` | Float | No | Measured value | The actual result — compared against spec to judge quality. | Measure. |
| `target` | Float | No | Target spec | The benchmark the result is judged against. | |
| `tolerance` | Float | No | Acceptable +/- variance | Defines the in-spec window for the result. | |
| `unit` | String | No | Measurement unit | Makes the value interpretable against spec. | |
| `pass_fail` | String | No | Pass / Fail result | The compliance outcome — the core quality KPI. | |
| `test_datetime` | Timestamp | No | When the test was performed | Timing of the check, for in-process vs. final QA analysis. | |

---

## 10. `fact_sales_order_dim` — Sales Order Fact

**Grain:** One row per sales order.  **Key:** `order_id`

**Business context:** The commercial outcome — what was sold, to whom, and at what value and margin. It is the revenue and profitability backbone, and via `run_id` it links every sale back to the batch and farms that produced it.

| Column | Type | Nullable | Description | Business context | Notes |
|---|---|---|---|---|---|
| `order_id` | String | No | Order identifier | The unit of sale — the grain for revenue and fulfillment reporting. | Degenerate dimension. |
| `date_key` | Integer | No | FK → `date_dim.date_key` | Enables sales and revenue trending over time. | Derived from `order_date`. |
| `product_key` | String | No | FK → `product_dim.product_key` | Attributes revenue to the SKU sold. | |
| `customer_key` | String | No | FK → `customer_dim.customer_key` | Attributes revenue to the customer/market. | |
| `run_id` | String | No | FK → `fact_production_run_dim.run_id` | The link that makes a sold product traceable back to its source. | Enables order → run → lots traceability. |
| `order_date` | Date | No | Order date | When the sale occurred — for revenue timing and seasonality. | |
| `customer` | String | No | Customer name | The buying account. | Denormalized. |
| `country` | String | No | Customer country | Destination market for export reporting. | Denormalized. |
| `region` | String | No | Sales region | Territory grouping for sales performance. | Denormalized. |
| `channel` | String | No | Sales channel | Route to market for channel economics. | Denormalized. |
| `is_domestic` | Boolean | No | Domestic vs. export | The home-vs-export revenue split. | |
| `is_organic` | Boolean | No | Organic SKU flag | Sizes the premium organic business. | |
| `product` | String | No | SKU sold | The product on the order line. | Denormalized. |
| `quantity_units` | Integer | No | Units ordered | Sales volume measure. | Measure. |
| `unit_price_usd` | Float | No | Unit price (USD) | Pricing measure for price realization analysis. | Measure. |
| `revenue_usd` | Float | No | Revenue (USD) | The primary revenue measure (reporting currency). | Measure. |
| `revenue_local` | Float | No | Revenue (local currency) | Revenue in the transaction currency for local reconciliation. | Measure. |
| `currency` | String | No | Local currency code | Identifies the transaction currency. | e.g. `VND`, `USD`. |
| `margin_pct` | Float | No | Margin percentage | Profitability rate — a core commercial KPI. | Measure. |
| `margin_usd` | Float | No | Margin (USD) | Absolute profit contribution of the order. | Measure. |
| `on_time_delivery` | Boolean | No | On-time delivery flag | Service-level KPI for fulfillment reliability. | |

---

## 11. `bridge_lot_run_dim` — Lot ↔ Run Bridge

**Grain:** One row per (run, lot) pair.  **Composite key:** (`run_id`, `lot_id`)

**Business context:** The traceability backbone that records which farmer lots went into which production run. It resolves the many-to-many between supply and production and is what makes farm-to-product (and product-to-farm) tracing possible for certification audits.

| Column | Type | Nullable | Description | Business context | Notes |
|---|---|---|---|---|---|
| `run_id` | String | No | FK → `fact_production_run_dim.run_id` | The production batch side of the supply-to-production link. | |
| `lot_id` | String | No | FK → `fact_intake_dim.lot_id` | The incoming-supply side of the link — the lot consumed. | |
| `farmer_key` | Integer | No | FK → `farmer_dim.farmer_key` | Carries the source farm so traceability resolves in one hop. | Denormalized for fast traceability joins. |
| `weight_consumed` | Float | No | Weight of the lot used in the run (kg) | How much of each lot fed the batch — supports mass-balance and contribution analysis. | Measure. |

**Traceability:** join `fact_sales_order_dim` → `bridge_lot_run_dim` (on `run_id`) → `farmer_dim` (on `farmer_key`) to trace any Cocoxim order back to the supplying farmers — the backbone for EU/USDA organic certification audits.
