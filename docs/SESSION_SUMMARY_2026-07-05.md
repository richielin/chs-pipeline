# CHS Pipeline — Session Summary

**Session:** 2026-07-05 ~22:00 ET
**Next action:** Wait for Richie to resume. Quota resets ~06:20 ET.

---

## Project Overview

Extract structured data from NYC Correctional Health Services (CHS) PDF reports — Patient Profile (1-page charts) and Access Report (multi-page tables) — into time-series CSVs.

**GitHub:** https://github.com/richielin/chs-pipeline

---

## Phase 1: Patient Profile Pipeline ✅ COMPLETE

### Architecture
```
PDF → render.py (pypdfium2) → PNG → parse_patient_profile.py (Vision AI) → dict
  → validate.py (Pydantic + semantic) → result.json → curate.py → patient_profile_monthly.csv
```

### Files Built

| File | Lines | Purpose |
|------|-------|---------|
| `src/chs_pipeline/__init__.py` | — | Package init |
| `src/chs_pipeline/render.py` | 25 | PDF → PNG via pypdfium2 |
| `src/chs_pipeline/schemas.py` | 110 | Pydantic models: CensusLOS, AgeDistribution, ScoreCard, Conditions, PatientProfileResult |
| `src/chs_pipeline/parse_patient_profile.py` | 106 | Vision-based extraction via agy/Gemini |
| `src/chs_pipeline/validate.py` | 127 | Schema validation + semantic checks (ADC 0–20000, % 0–100, age 18–80, LOS 1–365) + confidence scoring |
| `src/chs_pipeline/runner.py` | 136 | Orchestrator: render → parse → validate → result.json |
| `src/chs_pipeline/curate.py` | 83 | Merge all result.json → patient_profile_monthly.csv |
| `src/chs_pipeline/agy_utils.py` | 157 | Shared agy call utility with transcript fallback |
| `scripts/run_pipeline.py` | 148 | CLI: `--type patient_profile|access_report --provider gemini|bedrock` |
| `scripts/backfill.py` | 35 | Batch processor: recursive PDF → runner |
| `prompts/pp_extract_v1.txt` | 80 | Vision prompt for Patient Profile (5 chart modules → JSON) |

### Backfill Results

| Metric | Value |
|--------|-------|
| Total PDFs | 33 (Aug 2023 – May 2026) |
| Successfully processed | 32 (2023-09 missing from source — 404 on Azure) |
| Curated CSV rows | 33 unique months |
| Avg confidence | 0.925 |
| Data trend | ADC 6,268→7,732→6,744; Homeless % 25–29%; Medicaid 76–86% |

### Output Format (result.json)
```json
{
  "document_id": "2026-05",
  "report_month": "2026-05",
  "confidence": 1.0,
  "modules": {
    "census_los": {"average_daily_census": 6744, "median_length_of_stay_days": 151, "confidence": 1.0},
    "age_distribution": {"pct_18_21": 8.0, "pct_55_plus": 10.0, "median_age": 35, "confidence": 1.0},
    "homeless": {"percentage": 29.0, "confidence": 1.0},
    "medicaid": {"percentage": 85.0, "confidence": 1.0},
    "conditions": {"mental_health_history_pct": 60.0, "substance_use_history_pct": 31.0, "chronic_medical_history_pct": 28.0, "confidence": 1.0}
  }
}
```

---

## Phase 2: Access Report Pipeline ✅ CODE READY (needs execution)

### Architecture
```
PDF → render.py → PNGs[1..N] → parse_access_report.py (Vision per page, classify + extract)
  → validate.py → result.json → curate.py → access_report_summary.csv + access_report_facility.csv
```

### Files Built

| File | Lines | Purpose |
|------|-------|---------|
| `src/chs_pipeline/parse_access_report.py` | 222 | Multi-page Vision parser: classify page (summary/facility/other), extract table data, aggregate |
| `prompts/ar_extract_v1.txt` | 80 | Combined prompt: page classification + table extraction + facility code ID |
| `src/chs_pipeline/schemas.py` | +40 | Added: ARMetric, FacilityData, AccessReportResult |
| `src/chs_pipeline/validate.py` | +20 | Added: validate_access_report() |
| `src/chs_pipeline/runner.py` | +80 | Added: process_access_report() |

### AR Sample PDFs (5, downloaded)

| File | Pages | Type |
|------|-------|------|
| `2026-04.pdf` | 13 | Monthly — latest format |
| `2025-Q2.pdf` | 46 | Quarterly (transition) |
| `2024-Q1.pdf` | 47 | Quarterly (mid) |
| `2022-Q3.pdf` | 46 | Quarterly (early) |
| `2019-03.pdf` | 28 | Monthly (old format) |

### Page Structure (2026-04)
- P1: Cover (→ other)
- P2: Table of Contents (→ other)
- P3: Data Dictionary (→ other)
- **P4: "III. Access Report Summary" → summary** (section 1.x–5.x tables)
- P5: "IV. Access Report BHTU" → facility
- **P6+: "V. Access Report EMTC" → facility** (one page per facility)
- Facilities identified: EMTC, GRVC, NIC, OBCC, RESH, RMSC, RNDC, WF, AMKC, VCBC, BKDC, BHTU

---

## Known Issues

### 1. agy --print stdout not captured
`agy --dangerously-skip-permissions --print` runs the model but stdout is not returned (documented agy limitation).
**Fix applied:** `src/chs_pipeline/agy_utils.py` reads from agy's conversation transcript files as fallback.

### 2. Gemini Individual quota exhausted
After ~33 Vision calls, got `RESOURCE_EXHAUSTED (code 429)`. Quota resets ~4h6m from last hit.
**Next session:** Run AR backfill in batches of 10-15, not all at once.

### 3. 2023-09 Patient Profile missing
The September 2023 PDF returns 404 from Azure blob storage (confirmed via curl with multiple URL patterns).
**Handling:** Missing month recorded — no action needed.

### 4. CRLF warnings in git
Windows git-bash emits LF→CRLF warnings. Non-blocking — git handles transparently.

---

## Resume Checklist (for next session)

### If quota is fresh:
```bash
cd ~/projects/chs-data-pipeline

# 1. Verify PP parser works (single test)
python scripts/run_pipeline.py data/raw/patient_profiles/2026-05.pdf --type patient_profile

# 2. Verify AR parser (test one page)
python scripts/run_pipeline.py data/raw/access_reports/2026-04.pdf --type access_report --output-dir data/output/test-ar

# 3. Download all Access Report PDFs
# URL pattern: https://hhinternet.blob.core.windows.net/uploads/{year}/{month}/chs-access-report-{name}-{year}.pdf
# Full list on CHS publications page (no bot detection)
python scripts/backfill.py --dir data/raw/access_reports --output-dir data/output --type access_report

# 4. Generate curated CSVs
python -c "from src.chs_pipeline.curate import curate_access_report; ..."
```

### Key Data Locations
| Data | Path |
|------|------|
| Repo root (git) | `~/projects/chs-data-pipeline/` |
| PP raw PDFs | `data/raw/patient_profiles/` (32 files) |
| AR raw PDFs | `data/raw/access_reports/` (5 samples) |
| PP results | `data/output/<YYYY-MM>/result.json` (33 dirs) |
| AR samples | `data/raw/access_reports/*.pdf` (5 files) |
| Master CSV | `data/output/patient_profile_monthly.csv` |
| GitHub | `https://github.com/richielin/chs-pipeline` |

### Priority (quota-limited)
1. 🥇 Test AR on 1 sample → validate page classification
2. 🥇 Download remaining ~40 AR PDFs (no agy needed — just curl)
3. 🥈 Batch AR backfill (10–15 at a time, wait between batches)
4. 🥉 Curate AR CSVs + push to GitHub
