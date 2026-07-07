# Patient Profile Extractor — Specification

## Source
CHS Patient Profile for Individuals in the NYC Jail System
https://www.nychealthandhospitals.org/correctionalhealthservices/publications-reports/

## Input
PDF file (1 page), rendered to PNG and sent to Vision AI (Gemini) with structured extraction prompt

## Output
Single CSV file: `patient_profile_monthly.csv`
Append mode — each run adds the newest month's row.

## CSV Schema
```csv
month,avg_daily_census,median_los_days,pct_age_18_21,pct_age_55_plus,median_age,pct_homeless,pct_medicaid,pct_mh_enrolled,pct_serious_mh,pct_alcohol_use,pct_opioid_use,pct_pulmonary,pct_cardiovascular,pct_neurologic,pct_endocrine,pct_renal,pct_malignancy,pct_hepatitis,pct_hiv
```

Types: month=DATE, all others=FLOAT or INT

## PDF Layout (fixed, 5 modules)

### Module 1 — Top-Left: ADC & LOS chart
Vision AI interprets the visual layout of the chart/scorecard. The chart has:
- Left y-axis: 8000, 7500, 7000, 6500, 6000, 5500, 5000 (ADC)
- Right y-axis: 160, 150, 140, 130, 120, 110, 100 (LOS)
- x-axis: JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC
- Bar chart for ADC values
- Line chart for LOS values
- Legend: "Census" and "Length of Stay, median (days)"

Strategy: Vision AI extracts the latest month's ADC (bar height) and LOS (line value) visually.

### Module 2 — Top-Right: Age % & Median Age chart
- Left y-axis: 16, 14, 12, 10, 8, 6, 4, 2, 0 (ages 18-21 and 55+ %)
- Right y-axis: 35, 34, 33, 32, 31, 30 (median age)
- Three data series: 18-21%, 55+%, median age
- Legend: "Age 18-21, %", "Age 55+, %", "Age, median"

Strategy: Vision AI extracts the latest month's values visually.

### Module 3 — Middle-Left: Homelessness scorecard
- "Homeless or Likely to be Homeless"
- Large percentage value (e.g., "29%")
- Below: descriptive text

Strategy: Vision AI reads the large percentage value next to the heading.

### Module 4 — Middle-Right: Medicaid scorecard
- "Have Medicaid Coverage"
- Large percentage value (e.g., "85%")

Strategy: Vision AI reads the large percentage value next to the heading.

### Module 5 — Bottom: Health Conditions bar chart
- Sections: MENTAL HEALTH, SUBSTANCE USE, CHRONIC MEDICAL CONDITIONS
- Horizontal bars with percentage labels
- Need: pct_mh_enrolled, pct_serious_mh, pct_alcohol_use, pct_opioid_use, pct_pulmonary, pct_cardiovascular, pct_neurologic, pct_endocrine, pct_renal, pct_malignancy, pct_hepatitis, pct_hiv

Strategy: Vision AI reads the bar length or value label for each condition.

## Edge Cases
- PDF may show only 5 months of data (Jan-May 2026) or fewer
- Some months may be missing from the axis
- Only extract the LATEST month's complete data row
- If a value is missing, use NULL

## Output Path
`~/projects/chs-data-pipeline/data/output/patient_profile_monthly.csv`

## Verification
After extraction, print a summary of extracted values and compare visually with the PDF.