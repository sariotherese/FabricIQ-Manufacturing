"""
Generate synthetic quality test results for the Betrimex Fabric demo.

Each production run has multiple QA tests (microbiological, brix, pH,
color, viscosity, fill volume). Test results are influenced by the run's
average brix and grade — low-quality input correlates with more failures.

Output: 01_data/raw/quality_tests.csv  (~120,000 rows)
"""

import random
from datetime import timedelta
from pathlib import Path
import pandas as pd

# ---- Config ----
SEED = 42
TESTS_PER_RUN_MIN = 4
TESTS_PER_RUN_MAX = 8

# ---- Paths ----
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR.parent / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
RUNS_FILE = RAW_DIR / "production_runs.csv"
OUTPUT_FILE = RAW_DIR / "quality_tests.csv"

if not RUNS_FILE.exists():
    raise FileNotFoundError(
        f"production_runs.csv not found. Run gen_production_runs.py first."
    )

random.seed(SEED)

# ---- Load runs ----
print(f"Loading runs from {RUNS_FILE.name}...")
runs_df = pd.read_csv(RUNS_FILE, parse_dates=["start_datetime", "end_datetime"])
print(f"Loaded {len(runs_df):,} runs")

# ---- Test catalog ----
# Each test has: name, category, target value, tolerance, unit
TEST_CATALOG = {
    "Brix":                {"category": "Chemical",         "target": 6.0,   "tol": 1.0,  "unit": "°Bx"},
    "pH":                  {"category": "Chemical",         "target": 5.2,   "tol": 0.4,  "unit": "pH"},
    "Total Plate Count":   {"category": "Microbiological",  "target": 100,   "tol": 200,  "unit": "CFU/mL"},
    "Yeast & Mold":        {"category": "Microbiological",  "target": 10,    "tol": 20,   "unit": "CFU/mL"},
    "Coliform":            {"category": "Microbiological",  "target": 0,     "tol": 1,    "unit": "CFU/mL"},
    "Color L*":            {"category": "Physical",         "target": 92,    "tol": 4,    "unit": "L*"},
    "Viscosity":           {"category": "Physical",         "target": 1.2,   "tol": 0.3,  "unit": "cP"},
    "Fill Volume":         {"category": "Physical",         "target": 330,   "tol": 5,    "unit": "mL"},
    "Sodium":              {"category": "Chemical",         "target": 105,   "tol": 25,   "unit": "mg/L"},
    "Potassium":           {"category": "Chemical",         "target": 250,   "tol": 50,   "unit": "mg/L"},
}

ALL_TESTS = list(TEST_CATALOG.keys())

# ---- Generate ----
print("Generating quality tests...")
rows = []
test_counter = 0

for _, run in runs_df.iterrows():
    n_tests = random.randint(TESTS_PER_RUN_MIN, TESTS_PER_RUN_MAX)
    tests = random.sample(ALL_TESTS, n_tests)

    # Quality factor — runs with low brix or low Grade A % fail more often
    brix_factor = run["avg_brix"] / 6.5
    grade_factor = run["grade_a_pct"] / 100
    fail_prob = max(0.02, 0.18 - 0.10 * brix_factor - 0.05 * grade_factor)

    for test_name in tests:
        cfg = TEST_CATALOG[test_name]
        test_counter += 1

        # 90%+ of tests pass; rest hit out-of-spec values
        passes = random.random() > fail_prob

        if passes:
            # Inside tolerance — small normal variation around target
            value = random.normalvariate(cfg["target"], cfg["tol"] / 3)
        else:
            # Outside tolerance — push past the limit
            direction = random.choice([-1, 1])
            value = cfg["target"] + direction * cfg["tol"] * random.uniform(1.1, 1.8)

        # Microbiological values can't be negative
        if cfg["category"] == "Microbiological":
            value = max(0, value)

        # Test datetime: during or shortly after the run
        test_dt = run["start_datetime"] + timedelta(
            minutes=random.randint(15, int(run["duration_hours"] * 60) + 60)
        )

        rows.append({
            "test_id":      f"QT-{test_counter:08d}",
            "run_id":       run["run_id"],
            "test_name":    test_name,
            "category":     cfg["category"],
            "value":        round(value, 2),
            "target":       cfg["target"],
            "tolerance":    cfg["tol"],
            "unit":         cfg["unit"],
            "pass_fail":    "Pass" if passes else "Fail",
            "test_datetime": test_dt.strftime("%Y-%m-%d %H:%M:%S"),
        })

    if (_ + 1) % 2_000 == 0:
        print(f"  {_ + 1:,} / {len(runs_df):,} runs processed")

# ---- Write ----
df = pd.DataFrame(rows)
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print(f"\nWrote {len(df):,} quality tests to {OUTPUT_FILE.name}")
print("\nPass / Fail distribution:")
print(df["pass_fail"].value_counts(normalize=True).round(3))
print("\nTests by category:")
print(df["category"].value_counts())
print("\nTop failing tests:")
fails = df[df["pass_fail"] == "Fail"]
print(fails["test_name"].value_counts().head())