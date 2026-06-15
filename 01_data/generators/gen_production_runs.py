"""
Generate synthetic production runs for the Betrimex Fabric demo.

Each run represents a batch processed on a specific plant line, consuming
a subset of coconut lots. Yield is computed from the quality (brix, grade)
of the consumed lots so the Data Agent can answer realistic "why did yield
drop?" questions during the demo.

Outputs:
  01_data/raw/production_runs.csv      (~20,000 rows)
  01_data/raw/lot_consumption.csv      (~1.5M rows, many-to-many bridge)
"""

import random
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# ---- Config ----
NUM_RUNS = 20_000
SEED = 42
LOTS_PER_RUN_MIN = 50
LOTS_PER_RUN_MAX = 200

# ---- Paths ----
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR.parent / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
LOTS_FILE = RAW_DIR / "lots.csv"
RUNS_FILE = RAW_DIR / "production_runs.csv"
CONSUMPTION_FILE = RAW_DIR / "lot_consumption.csv"

# ---- Sanity ----
if not LOTS_FILE.exists():
    raise FileNotFoundError(
        f"lots.csv not found at {LOTS_FILE}. Run gen_lots.py first."
    )

# ---- Determinism ----
random.seed(SEED)

# ---- Load lots ----
print(f"Loading lots from {LOTS_FILE.name}...")
lots_df = pd.read_csv(LOTS_FILE, parse_dates=["intake_date"])
print(f"Loaded {len(lots_df):,} lots")

# ---- Reference data ----
# Plants in Ben Tre, each with multiple lines and product specializations
PLANTS = {
    "Ben Tre Main Plant": {
        "lines": {
            "Line 1": ["Cocoxim Coconut Water Original 330ml",
                       "Cocoxim Coconut Water Original 1L"],
            "Line 2": ["Cocoxim Coconut Water Pink 330ml",
                       "Cocoxim Coconut Water Lychee 330ml"],
            "Line 3": ["Cocoxim Coconut Milk 400ml",
                       "Cocoxim Coconut Cream 400ml"],
        },
        "organic_only": False,
        "capacity_factor": 1.0,
    },
    "Ben Tre Organic Plant": {
        "lines": {
            "Line 1": ["Cocoxim Organic Coconut Water 330ml",
                       "Cocoxim Organic Coconut Water 1L"],
            "Line 2": ["Cocoxim Organic Coconut Milk 400ml",
                       "Cocoxim Organic Coconut Cream 400ml"],
        },
        "organic_only": True,
        "capacity_factor": 0.7,
    },
    "Ben Tre New Facility": {
        "lines": {
            "Line 1": ["Cocoxim Coconut Water Original 1L"],
            "Line 2": ["Desiccated Coconut Premium",
                       "Desiccated Coconut Fine"],
            "Line 3": ["Cocoxim Coconut Oil 500ml"],
            "Line 4": ["Cocoxim Coconut Milk 1L"],
        },
        "organic_only": False,
        "capacity_factor": 1.3,  # newer = bigger
    },
}

SHIFTS = [
    ("Morning",   6,  14),
    ("Afternoon", 14, 22),
    ("Night",     22, 30),  # +24 for overnight → handled below
]

# Map line + product → expected yield per kg of input coconut
# (Coconut water lines extract more liquid per kg than cream/oil lines)
def expected_yield_per_kg(product: str) -> float:
    if "Coconut Water" in product:
        return 0.42  # L per kg
    if "Coconut Milk" in product:
        return 0.30
    if "Coconut Cream" in product:
        return 0.18
    if "Desiccated" in product:
        return 0.12  # kg dry per kg fresh
    if "Coconut Oil" in product:
        return 0.05
    return 0.25

# ---- Build per-plant lot pools ----
print("Indexing lots by district and organic status...")
# Each plant pulls lots from Ben Tre province (and nearby), organic plant from organic farmers only
organic_lots = lots_df[lots_df["is_organic"] == True].reset_index(drop=True)
all_lots = lots_df.reset_index(drop=True)

# Pre-sort lots by intake_date so each production run uses lots from around the run date
all_lots_sorted = all_lots.sort_values("intake_date").reset_index(drop=True)
organic_lots_sorted = organic_lots.sort_values("intake_date").reset_index(drop=True)

# ---- Generate ----
print(f"Generating {NUM_RUNS:,} production runs...")
runs = []
consumption = []

plant_names = list(PLANTS.keys())
plant_weights = [PLANTS[p]["capacity_factor"] for p in plant_names]

# Spread runs evenly across the lots' date range
date_min = all_lots["intake_date"].min()
date_max = all_lots["intake_date"].max()
total_days = (date_max - date_min).days

for i in range(NUM_RUNS):
    plant = random.choices(plant_names, weights=plant_weights, k=1)[0]
    plant_cfg = PLANTS[plant]
    line = random.choice(list(plant_cfg["lines"].keys()))
    product = random.choice(plant_cfg["lines"][line])

    # Pick a date and shift
    run_day = date_min + timedelta(days=random.randint(0, total_days - 1))
    shift_name, start_h, end_h = random.choice(SHIFTS)
    start_dt = run_day.replace(hour=start_h % 24, minute=random.randint(0, 30))
    duration_hours = random.uniform(4, 10)
    end_dt = start_dt + timedelta(hours=duration_hours)

    # Pick lots: prefer lots delivered shortly before the run (freshness)
    lot_pool = organic_lots_sorted if plant_cfg["organic_only"] else all_lots_sorted
    freshness_window = pd.Timedelta(days=14)
    window_lots = lot_pool[
        (lot_pool["intake_date"] >= run_day - freshness_window) &
        (lot_pool["intake_date"] <= run_day)
    ]
    if len(window_lots) < LOTS_PER_RUN_MIN:
        # Fallback: widen window if not enough fresh lots
        window_lots = lot_pool[
            (lot_pool["intake_date"] >= run_day - pd.Timedelta(days=45)) &
            (lot_pool["intake_date"] <= run_day)
        ]
    if len(window_lots) < LOTS_PER_RUN_MIN:
        continue  # skip; not enough lots available

    n_lots = random.randint(
        LOTS_PER_RUN_MIN,
        min(LOTS_PER_RUN_MAX, len(window_lots))
    )
    chosen = window_lots.sample(n=n_lots, random_state=random.randint(0, 10**9))

    # Compute expected output (kg in → L or kg out)
    yield_factor = expected_yield_per_kg(product)
    input_weight_kg = chosen["weight_kg"].sum()
    expected_yield = round(input_weight_kg * yield_factor, 1)

    # Actual yield depends on quality of consumed lots
    avg_brix = chosen["brix"].mean()
    grade_a_pct = (chosen["grade"] == "A").mean()

    # Quality bonus/penalty (higher brix + more Grade A = closer to expected)
    quality_score = 0.5 * (avg_brix / 6.5) + 0.5 * (1 + grade_a_pct) / 2
    # Random downtime / line losses
    line_efficiency = random.normalvariate(0.93, 0.05)
    line_efficiency = max(0.70, min(line_efficiency, 1.00))

    actual_yield = round(expected_yield * quality_score * line_efficiency, 1)
    yield_pct = round(actual_yield / expected_yield * 100, 2) if expected_yield > 0 else 0

    # Downtime minutes (occasionally significant)
    downtime_min = max(0, int(random.expovariate(1 / 25)))
    if random.random() < 0.05:  # 5% of runs hit a major issue
        downtime_min += random.randint(60, 240)

    run_id = f"RUN-{i + 1:06d}"
    runs.append({
        "run_id":            run_id,
        "plant":             plant,
        "line":              line,
        "product":           product,
        "shift":             shift_name,
        "start_datetime":    start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime":      end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_hours":    round(duration_hours, 2),
        "input_weight_kg":   round(input_weight_kg, 1),
        "expected_yield":    expected_yield,
        "actual_yield":      actual_yield,
        "yield_pct":         yield_pct,
        "avg_brix":          round(avg_brix, 2),
        "grade_a_pct":       round(grade_a_pct * 100, 2),
        "downtime_minutes":  downtime_min,
        "is_organic_run":    plant_cfg["organic_only"],
        "num_lots_consumed": n_lots,
    })

    # Lot consumption bridge — proportional split of each lot's weight
    for _, lot in chosen.iterrows():
        consumption.append({
            "run_id":           run_id,
            "lot_id":           lot["lot_id"],
            "farmer_id":        lot["farmer_id"],
            "weight_consumed":  lot["weight_kg"],  # assume full lot per run
        })

    if (i + 1) % 2_000 == 0:
        print(f"  {i + 1:,} / {NUM_RUNS:,} runs")

# ---- Write ----
runs_df = pd.DataFrame(runs)
consumption_df = pd.DataFrame(consumption)

runs_df.to_csv(RUNS_FILE, index=False, encoding="utf-8")
consumption_df.to_csv(CONSUMPTION_FILE, index=False, encoding="utf-8")

print(f"\nWrote {len(runs_df):,} runs to {RUNS_FILE.name}")
print(f"Wrote {len(consumption_df):,} lot-consumption rows to {CONSUMPTION_FILE.name}")

print("\nSample runs:")
print(runs_df.head(5).to_string(index=False))
print("\nYield % distribution:")
print(runs_df["yield_pct"].describe().round(2))
print("\nRuns by plant:")
print(runs_df["plant"].value_counts())
print("\nRuns by product:")
print(runs_df["product"].value_counts().head(10))