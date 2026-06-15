# Generate 30,000 synthetic farmers across Ben Tre, Tra Vinh, Tien Giang,
# and Vinh Long with realistic Vietnamese names, districts, and organic
# certifications. Output to ../raw/farmers.csv

import csv
from pathlib import Path
from faker import Faker

faker = Faker("vi_VN")

districts = ["Ben Tre", "Tra Vinh", "Tien Giang", "Vinh Long"]
organic_certifications = ["Certified Organic", "Non-Organic"]

# Build an absolute path based on this script's location
SCRIPT_DIR = Path(__file__).resolve().parent          # ...\01_data\generators
RAW_DIR = SCRIPT_DIR.parent / "raw"                   # ...\01_data\raw
RAW_DIR.mkdir(parents=True, exist_ok=True)            # create folder if missing
OUTPUT_FILE = RAW_DIR / "farmers.csv"

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["farmer_id", "name", "district", "organic_certification"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for i in range(30000):
        writer.writerow({
            "farmer_id": i + 1,
            "name": faker.name(),
            "district": faker.random.choice(districts),
            "organic_certification": faker.random.choice(organic_certifications)
        })

print(f"Wrote 30,000 farmers to {OUTPUT_FILE}")