from pathlib import Path

out_path = Path("00_docs/farmer_feedback_observations_lots_additional.pdf")

lines = [
    "Betrimex Farmer Feedback and Observations by Lot (Additional)",
    "Reference basis: Gold data dictionary + data source description (fact_intake fields).",
    "Referential integrity: lot_id -> farmer_id validated against raw lots.csv and farmers.csv.",
    "",
    "1) Lot: LOT-0000617",
    "- Farmer ID: 19230",
    "- Farmer Name: Co Huong Le",
    "- District: Tra Vinh",
    "- Certification: Certified Organic",
    "- Intake Date: 2025-10-22",
    "- Collection Point: Cang Long Hub",
    "- Weight (kg): 132.5",
    "- Brix: 5.59",
    "- Grade: B",
    "- Organic Lot: True",
    "- Positive Remark: Harvest compliance was good and organic documentation was complete.",
    "- Negative Remark: Lot sweetness and volume were below preferred target levels.",
    "- Operations Observation: Small lot size with moderate brix; monitor next deliveries for uplift.",
    "",
    "2) Lot: LOT-0008098",
    "- Farmer ID: 5077",
    "- Farmer Name: An Bao Hoang",
    "- District: Vinh Long",
    "- Certification: Certified Organic",
    "- Intake Date: 2025-10-22",
    "- Collection Point: Vung Liem Hub",
    "- Weight (kg): 109.5",
    "- Brix: 6.15",
    "- Grade: B",
    "- Organic Lot: True",
    "- Positive Remark: Delivery timing was reliable and brix was acceptable for processing.",
    "- Negative Remark: Delivered volume was low, limiting run planning flexibility.",
    "- Operations Observation: Good compliance signal but constrained by low intake weight.",
    "",
    "3) Lot: LOT-0006984",
    "- Farmer ID: 26602",
    "- Farmer Name: Nhat Hoang",
    "- District: Ben Tre",
    "- Certification: Non-Organic",
    "- Intake Date: 2026-03-13",
    "- Collection Point: Giong Trom Hub",
    "- Weight (kg): 235.9",
    "- Brix: 5.82",
    "- Grade: A",
    "- Organic Lot: False",
    "- Positive Remark: Strong lot size and Grade A classification supported production readiness.",
    "- Negative Remark: Brix was modest for a Grade A lot, indicating quality-mix variability.",
    "- Operations Observation: High-utility lot for volume; follow-up on sweetness consistency.",
]

# Minimal PDF writer (no external dependencies)
PAGE_W, PAGE_H = 612, 792
LEFT, TOP = 50, 742
LINE_H = 14
FONT = "/F1 10 Tf"

pages = []
current = []
y = TOP
for line in lines:
    if y < 60:
        pages.append(current)
        current = []
        y = TOP
    # Escape PDF text operators
    safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    current.append(f"BT {FONT} 1 0 0 1 {LEFT} {y} Tm ({safe}) Tj ET")
    y -= LINE_H
if current:
    pages.append(current)

objs = []

def add_obj(body: str) -> int:
    objs.append(body)
    return len(objs)

font_id = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
page_ids = []
content_ids = []

for page_lines in pages:
    stream = "\n".join(page_lines).encode("latin-1", "replace")
    content_id = add_obj(f"<< /Length {len(stream)} >>\nstream\n" + stream.decode("latin-1", "replace") + "\nendstream")
    content_ids.append(content_id)

pages_id = add_obj("")  # placeholder

for cid in content_ids:
    page_id = add_obj(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {cid} 0 R >>")
    page_ids.append(page_id)

kids = " ".join(f"{pid} 0 R" for pid in page_ids)
objs[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"

catalog_id = add_obj(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

pdf = ["%PDF-1.4\n"]
offsets = [0]
for i, body in enumerate(objs, start=1):
    offsets.append(sum(len(p.encode("latin-1", "replace")) for p in pdf))
    pdf.append(f"{i} 0 obj\n{body}\nendobj\n")

xref_pos = sum(len(p.encode("latin-1", "replace")) for p in pdf)
pdf.append(f"xref\n0 {len(objs)+1}\n")
pdf.append("0000000000 65535 f \n")
for i in range(1, len(objs)+1):
    pdf.append(f"{offsets[i]:010d} 00000 n \n")
pdf.append(f"trailer\n<< /Size {len(objs)+1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n")

out_path.write_bytes("".join(pdf).encode("latin-1", "replace"))
print(f"Created {out_path}")
