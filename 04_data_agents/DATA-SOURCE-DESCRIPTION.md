# Betrimex Coconut Operations — Data Source

**Location:** `agri_lakehouse.golddb`  
**Tables:** 13 (6 dimensions + 4 facts + 1 bridge + 2 inventory)  
**Updated:** Daily  

## What This Is

A star-schema data warehouse capturing Betrimex's entire coconut supply chain: from ~200 smallholder farmers in the Mekong Delta, through multi-line production facilities, quality testing, domestic and export sales, to daily finished-goods inventory across 3 distribution centers.

## What It Represents

**Supply:** Farmer deliveries (lot intake), quality grades, brix (sugar content), organic certification  
**Production:** Plant & line yields, downtime, efficiency KPIs; input-to-output traceability via production runs and lots  
**Quality:** Lab & line test results (chemical, microbiological, physical) vs. specifications  
**Sales:** Orders, revenue, margin, channel (domestic/export), on-time delivery by customer  
**Inventory:** Daily stock positions and restock alerts at each DC, with recommended replenishment quantities  

## Why Use It

Answer operational questions without waiting for static reports:
- "Why did yield drop yesterday?" → Drill into runs, lots, tests, input quality
- "Which farmers are at supply risk?" → Combine organic flags, brix trends, delivery history
- "What SKUs need reordering now?" → Latest inventory alerts with urgency ranking (days of supply)
- "Show me revenue by channel YTD" → Sales orders grouped by customer region/channel
- "Trace an order back to its source farmers" → Bridge/lot/intake/farmer tables for full traceability
- "Compare yields by plant/line/shift" → Production runs with efficiency bands and root-cause drivers
