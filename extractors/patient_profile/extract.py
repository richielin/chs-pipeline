#!/usr/bin/env python3
"""
Patient Profile Extractor — Vision-based via Gemini/agy.

Converts PDF page to image, sends to Gemini for structured data extraction.
"""

import json, os, re, subprocess, sys, uuid
from datetime import datetime

import pypdfium2 as pdfium

FIELD_NAMES = [
    "month","avg_daily_census","median_los_days",
    "pct_age_18_21","pct_age_55_plus","median_age",
    "pct_homeless","pct_medicaid",
    "pct_mh_enrolled","pct_serious_mh","pct_alcohol_use","pct_opioid_use",
    "pct_pulmonary","pct_cardiovascular","pct_neurologic","pct_endocrine",
    "pct_renal","pct_malignancy","pct_hepatitis","pct_hiv",
]


def pdf_to_png(pdf_path: str, scale: float = 2.0) -> str:
    """Render first page as PNG, return path."""
    pdf = pdfium.PdfDocument(pdf_path)
    page = pdf[0]
    bitmap = page.render(scale=scale)
    img = bitmap.to_pil()
    png_path = pdf_path.replace('.pdf', f'_{uuid.uuid4().hex[:8]}.png')
    img.save(png_path)
    pdf.close()
    return png_path


def build_prompt(png_path: str) -> str:
    """Build the extraction prompt for Gemini."""
    return f"""Look at the image at {png_path}. This is a CHS Patient Profile PDF for the NYC Jail System.

Extract ALL numeric data from this 1-page report. Return ONLY valid JSON with these exact fields.
Use null ONLY if the value is genuinely not visible.

IMPORTANT: Read the charts carefully. Here is the layout:

=== TOP-LEFT CHART: Average Daily Census & Median LOS ===
Line+bar chart with months on x-axis (JAN through DEC, may only show up to current month).
Left y-axis: Average Daily Census (5000-8000)
Right y-axis: Median Length of Stay (100-160 days)
Find the LATEST month's values:
- avg_daily_census: the bar height for the latest month
- median_los_days: the line value for the latest month

=== TOP-RIGHT CHART: Age Distribution ===
Three data series:
- Age 18-21% (left y-axis, ~0-16%)
- Age 55+% (left y-axis, ~0-16%)  
- Median Age (right y-axis, ~30-35)
Find the LATEST month's values.

=== MIDDLE SCORECARDS ===
Two large percentage values side by side:
- pct_homeless: "Homeless or Likely to be Homeless" percentage
- pct_medicaid: "Have Medicaid Coverage" percentage

=== BOTTOM BAR CHART: Health Conditions ===
Three sections with horizontal bars. Values are percentages.
Colors: Mental Health bars are one color, Substance Use another, Chronic Medical another.

MENTAL HEALTH section:
- pct_mh_enrolled = "Enrolled in mental health services" bar
- pct_serious_mh = "Serious mental illness" bar

SUBSTANCE USE section:
- pct_alcohol_use = "Alcohol use disorder" bar
- pct_opioid_use = "Opioid use disorder" bar

CHRONIC MEDICAL CONDITIONS section:
- pct_pulmonary = "Pulmonary: Asthma, COPD, and other lung disease"
- pct_cardiovascular = "Cardiovascular: Hypertension, ischemic heart disease..."
- pct_neurologic = "Neurologic: Epilepsy & related disorders..."
- pct_endocrine = "Endocrine: Diabetes mellitus"
- pct_renal = "Renal: Chronic kidney disease stage 3+"
- pct_malignancy = "Malignancy"
- pct_hepatitis = "Hepatitis B/C"
- pct_hiv = "HIV/AIDS"

Return this exact JSON structure:
{{
  "month": "2026-05-01",
  "avg_daily_census": 6744,
  "median_los_days": 151,
  "pct_age_18_21": 10,
  "pct_age_55_plus": 35,
  "median_age": 32,
  "pct_homeless": 29,
  "pct_medicaid": 85,
  "pct_mh_enrolled": 60,
  "pct_serious_mh": 31,
  "pct_alcohol_use": 26,
  "pct_opioid_use": 17,
  "pct_pulmonary": 28,
  "pct_cardiovascular": 17,
  "pct_neurologic": 9,
  "pct_endocrine": 6,
  "pct_renal": 3,
  "pct_malignancy": 1,
  "pct_hepatitis": 4,
  "pct_hiv": 3
}}
Return ONLY the JSON object, no other text, no markdown formatting."""


def extract(pdf_path: str) -> dict:
    """Extract data from Patient Profile PDF using vision."""
    # 1. Render PDF to PNG
    png_path = pdf_to_png(pdf_path)

    # 2. Build prompt
    prompt = build_prompt(png_path)

    # 3. Run agy with the prompt and get JSON back directly from stdout
    agy_path = os.path.expanduser("~/AppData/Local/agy/bin/agy")
    result = subprocess.run(
        [agy_path, "--dangerously-skip-permissions", "--print", prompt],
        capture_output=True, text=True, timeout=120,
        env={**os.environ}
    )

    # 4. Parse JSON from model output
    json_result = None
    output = result.stdout.strip()
    if output:
        json_match = re.search(r'\{[^{}]*"month"[^{}]*\}', output, re.DOTALL)
        if json_match:
            try:
                json_result = json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

    # 5. Cleanup PNG
    if os.path.exists(png_path):
        os.remove(png_path)

    return json_result or {}


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    raw_result = extract(pdf_path)

    # Always ensure all fields exist
    result = {f: raw_result.get(f, None) for f in FIELD_NAMES}

    # Output to CSV
    import csv
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "output")
    os.makedirs(base, exist_ok=True)
    out = os.path.join(base, "patient_profile_monthly.csv")

    fe = os.path.exists(out) and os.path.getsize(out) > 0
    with open(out, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELD_NAMES)
        if not fe:
            w.writeheader()
        w.writerow(result)

    print(f"✅ {os.path.basename(pdf_path)}")
    for f in FIELD_NAMES:
        v = result.get(f)
        print(f"   {f}: {v if v is not None else '—'}")
    print(f"   → {out}")


if __name__ == "__main__":
    main()
