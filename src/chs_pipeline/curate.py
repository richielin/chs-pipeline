"""Curate extracted Patient Profile results into time-series CSV output.

Scans an output directory for ``result.json`` files produced by the
pipeline runner, merges them into a single CSV, and writes it to
``patient_profile_monthly.csv``.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


# ── CSV field definitions ────────────────────────────────────────────

# Maps: CSV column name → dotted path into the result dict
CSV_FIELDS: list[tuple[str, tuple[str, ...]]] = [
    ("document_id", ("document_id",)),
    ("report_month", ("report_month",)),
    ("source_type", ("source_type",)),
    ("template_version", ("template_version",)),
    ("processed_at", ("processed_at",)),
    ("confidence", ("confidence",)),
    # census_los
    ("average_daily_census", ("modules", "census_los", "average_daily_census")),
    ("median_length_of_stay_days", ("modules", "census_los", "median_length_of_stay_days")),
    # age_distribution
    ("pct_18_21", ("modules", "age_distribution", "pct_18_21")),
    ("pct_55_plus", ("modules", "age_distribution", "pct_55_plus")),
    ("median_age", ("modules", "age_distribution", "median_age")),
    # scorecards
    ("homeless_pct", ("modules", "homeless", "percentage")),
    ("medicaid_pct", ("modules", "medicaid", "percentage")),
    # conditions — aggregated
    ("mental_health_history_pct", ("modules", "conditions", "mental_health_history_pct")),
    ("substance_use_history_pct", ("modules", "conditions", "substance_use_history_pct")),
    ("chronic_medical_history_pct", ("modules", "conditions", "chronic_medical_history_pct")),
    # conditions — individual Mental Health
    ("mh_enrolled_pct", ("modules", "conditions", "mh_enrolled_pct")),
    ("serious_mh_pct", ("modules", "conditions", "serious_mh_pct")),
    # conditions — individual Substance Use
    ("alcohol_use_pct", ("modules", "conditions", "alcohol_use_pct")),
    ("opioid_use_pct", ("modules", "conditions", "opioid_use_pct")),
    # conditions — individual Chronic Medical
    ("pulmonary_pct", ("modules", "conditions", "pulmonary_pct")),
    ("cardiovascular_pct", ("modules", "conditions", "cardiovascular_pct")),
    ("neurologic_pct", ("modules", "conditions", "neurologic_pct")),
    ("endocrine_pct", ("modules", "conditions", "endocrine_pct")),
    ("renal_pct", ("modules", "conditions", "renal_pct")),
    ("malignancy_pct", ("modules", "conditions", "malignancy_pct")),
    ("hepatitis_pct", ("modules", "conditions", "hepatitis_pct")),
    ("hiv_pct", ("modules", "conditions", "hiv_pct")),
]


def _resolve(data: dict, path: tuple[str, ...]) -> object:
    """Resolve a dotted path through nested dicts, returning ``None``
    for missing keys."""
    current: object = data
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _discover_results(output_dir: str) -> list[Path]:
    """Recursively find every ``result.json`` under *output_dir*."""
    base = Path(output_dir)
    if not base.is_dir():
        raise NotADirectoryError(f"Output directory not found: {output_dir}")
    return sorted(base.rglob("result.json"))


def curate_patient_profile(output_dir: str) -> str:
    """Scan *output_dir* for ``result.json`` files and write the
    consolidated time-series CSV.

    Parameters
    ----------
    output_dir:
        Root output directory containing per-document sub-folders
        (e.g. ``data/output/``).

    Returns
    -------
    str
        Absolute path to the generated CSV file.
    """
    result_files = _discover_results(output_dir)

    csv_path = Path(output_dir) / "patient_profile_monthly.csv"
    fieldnames = [col for col, _ in CSV_FIELDS]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for rf in result_files:
            data = json.loads(rf.read_text(encoding="utf-8"))
            row = {}
            for col, path in CSV_FIELDS:
                row[col] = _resolve(data, path)
            writer.writerow(row)

    return str(csv_path.resolve())
