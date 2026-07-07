#!/usr/bin/env python3
"""Remove test/verify dirs, re-run curate, report stats."""
import sys, shutil, os, csv, json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
for p in (_SRC, _REPO_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from src.chs_pipeline.curate import curate_patient_profile

# Clean up test/verify dirs  
for d in [_REPO_ROOT / "data/output/test", _REPO_ROOT / "data/output/verify"]:
    if d.exists():
        shutil.rmtree(d)
        print(f"Removed: {d}")

# Re-run curate
p = curate_patient_profile(str(_REPO_ROOT / "data/output"))
print(f"CSV: {p}")

# Stats
with open(p, 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Row count: {len(rows)}")
print(f"Columns: {reader.fieldnames}")
print()

confidences = [float(r.get('confidence', 0) or 0) for r in rows]
avg_conf = sum(confidences) / len(confidences) if confidences else 0
print(f"Average confidence: {avg_conf:.3f}")
print()

print("=== ALL ROWS ===")
for r in rows:
    print(f"  {r['report_month']:>8s}: census={r['average_daily_census']:>5s}, los={r['median_length_of_stay_days']:>3s}, conf={float(r['confidence']):.3f}, homeless={r['homeless_pct']:>4s}%, medicaid={r['medicaid_pct']:>4s}%")
