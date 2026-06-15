"""
Generate synthetic coconut lot deliveries for the Betrimex Fabric demo.

Each lot represents a batch of coconuts a farmer delivered to a collection
point. Lots are sampled from existing farmers (gen_farmers.py output) and
spread across the last 2 years.

Output: 01_data/raw/lots.csv  (~500,000 rows)
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from faker import Faker

# ---- Config ----
NUM_LOTS = 500_000
YEARS_OF_HISTORY = 2
SEED = 42

# ---- Paths ----
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR.parent / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
FARMERS_FILE = RAW_DIR / "farmers.csv"
OUTPUT_FILE = RAW_DIR / "lots.csv"

# ---- Sanity check ----
if not FARMERS_FILE.exists():
    raise FileNotFoundError(
        f"farmers.csv not found at {FARMERS_FILE}. "
        "Run gen_farmers.py first."
    )

# ---- Determinism ----
random.seed(SEED)
faker = Faker("vi_VN")
Faker.seed(SEED)

# ---- Load farmer pool ----
farmers_df = pd.read_csv(FARMERS_FILE)
print(f"Loaded {len(farmers_df):,} farmers from {FARMERS_FILE.name}")

# Build a quick lookup: farmer_id -> district (so lot collection point matches farmer's region)
farmer_district = dict(zip(farmers_df["farmer_id"], farmers_df["district"]))
farmer_organic = dict(zip(farmers_df["farmer_id"], farmers_df["organic_certification"]))
farmer_ids = farmers_df["farmer_id"].tolist()

# ---- Reference data ----
# Real-ish collection-point names per Mekong Delta province
COLLECTION_POINTS = {
    "Ben Tre":    ["Mo Cay Nam Hub", "Giong Trom Hub", "Chau Thanh Hub", "Binh Dai Hub", "Ba Tri Hub"],
    "Tra Vinh":   ["Cang Long Hub", "Cau Ke Hub", "Tieu Can Hub", "Tra Cu Hub"],
    "Tien Giang": ["Cho Gao Hub", "Go Cong Hub", "Cai Lay Hub"],
    "Vinh Long":  ["Vung Liem Hub", "Tra On Hub", "Binh Minh Hub"],
}

# Grade distribution — realistic for ag: most are A/B, few C
GRADES = ["A", "B", "C"]
GRADE_WEIGHTS = [0.60, 0.30, 0.10]

# ---- Generate ----
start_date = datetime.today() - timedelta(days=365 * YEARS_OF_HISTORY)
end_date = datetime.today()
total_days = (end_date - start_date).days

rows = []
print(f"Generating {NUM_LOTS:,} coconut lots across {total_days} days...")

for i in range(NUM_LOTS):
    farmer_id = random.choice(farmer_ids)
    district = farmer_district[farmer_id]
    organic = farmer_organic[farmer_id]

    # Collection point must be inside the farmer's district
    collection_point = random.choice(COLLECTION_POINTS[district])

    # Random intake date within the window
    intake_date = start_date + timedelta(days=random.randint(0, total_days))

    # Weight: typical smallholder delivery is 50–500 kg
    weight_kg = round(random.triangular(50, 500, 180), 1)

    # Brix (sugar content of coconut water) — typical 4.5–7.5
    brix = round(random.normalvariate(6.0, 0.6), 2)
    brix = max(3.5, min(brix, 8.5))

    # Grade — weighted random; organic farms skew higher quality
    if organic == "Certified Organic":
        grade = random.choices(GRADES, weights=[0.75, 0.22, 0.03])[0]
    else:
        grade = random.choices(GRADES, weights=GRADE_WEIGHTS)[0]

    rows.append({
        "lot_id":           f"LOT-{i + 1:07d}",
        "farmer_id":        farmer_id,
        "intake_date":      intake_date.strftime("%Y-%m-%d"),
        "collection_point": collection_point,
        "district":         district,
        "weight_kg":        weight_kg,
        "brix":             brix,
        "grade":            grade,
        "is_organic":       organic == "Certified Organic",
    })

    if (i + 1) % 100_000 == 0:
        print(f"  {i + 1:,} / {NUM_LOTS:,}")

# ---- Write ----
df = pd.DataFrame(rows)
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print(f"\nWrote {len(df):,} lots to {OUTPUT_FILE}")
print("\nSample rows:")
print(df.head(5).to_string(index=False))
print("\nGrade distribution:")
print(df["grade"].value_counts(normalize=True).round(3))
print("\nDistrict distribution:")
print(df["district"].value_counts())