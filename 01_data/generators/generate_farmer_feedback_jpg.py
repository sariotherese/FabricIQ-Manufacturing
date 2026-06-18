from pathlib import Path
from subprocess import run
from textwrap import wrap


out_path = Path("00_docs/farmer_feedback_observations_lots_additional.jpg")

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


wrapped_lines: list[str] = []
for line in lines:
    if not line:
        wrapped_lines.append("")
        continue
    wrapped_lines.extend(wrap(line, width=96) or [line])

ps_lines = []
for line in wrapped_lines:
    safe = line.replace("'", "''")
    ps_lines.append(f"'{safe}'")

ps_array = "@(" + ",\n    ".join(ps_lines) + ")"

ps_script = f"""
Add-Type -AssemblyName System.Drawing
$lines = {ps_array}
$title = 'Betrimex Farmer Feedback and Observations by Lot (Additional)'
$footer = 'Generated from referentially checked lot and farmer source rows.'
$font = New-Object System.Drawing.Font('Arial', 18, [System.Drawing.FontStyle]::Regular)
$titleFont = New-Object System.Drawing.Font('Arial', 26, [System.Drawing.FontStyle]::Bold)
$footerFont = New-Object System.Drawing.Font('Arial', 14, [System.Drawing.FontStyle]::Italic)
$margin = 70
$lineHeight = 28
$titleHeight = 42
$footerHeight = 30
$width = 1800
$height = [Math]::Max(1200, $margin * 2 + $titleHeight + ($lines.Count * $lineHeight) + $footerHeight + 40)
$bmp = New-Object System.Drawing.Bitmap($width, $height)
$gfx = [System.Drawing.Graphics]::FromImage($bmp)
$gfx.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
$gfx.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
$gfx.Clear([System.Drawing.Color]::White)
$black = [System.Drawing.Brushes]::Black
$gray = [System.Drawing.Brushes]::DimGray
$gfx.DrawString($title, $titleFont, $black, $margin, $margin)
$y = $margin + $titleHeight
foreach ($line in $lines) {{
    if ([string]::IsNullOrWhiteSpace($line)) {{
        $y += $lineHeight * 0.5
        continue
    }}
    $gfx.DrawString($line, $font, $black, $margin, $y)
    $y += $lineHeight
}}
$gfx.DrawString($footer, $footerFont, $gray, $margin, $height - 40)
$bmp.Save('{out_path.as_posix()}', [System.Drawing.Imaging.ImageFormat]::Jpeg)
$gfx.Dispose()
$bmp.Dispose()
Write-Output 'Created {out_path.as_posix()}'
"""

result = run([
    "pwsh",
    "-NoProfile",
    "-Command",
    ps_script,
], check=True, capture_output=True, text=True)
print(result.stdout.strip())
