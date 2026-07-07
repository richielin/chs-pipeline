"""Schema validation, semantic checks, and confidence scoring for
CHS Patient Profile extractions.

This module is intentionally *pure* — it never calls external APIs.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from chs_pipeline.schemas import PatientProfileResult

# ── Semantic bounds ──────────────────────────────────────────────────

SEMANTIC_BOUNDS: dict[str, tuple[float, float]] = {
    # (min, max)
    "census_los.average_daily_census": (0, 20000),
    "census_los.median_length_of_stay_days": (1, 365),
    "age_distribution.pct_18_21": (0, 100),
    "age_distribution.pct_55_plus": (0, 100),
    "age_distribution.median_age": (18, 80),
    "homeless.percentage": (0, 100),
    "medicaid.percentage": (0, 100),
    "conditions.mental_health_history_pct": (0, 100),
    "conditions.substance_use_history_pct": (0, 100),
    "conditions.chronic_medical_history_pct": (0, 100),
    "conditions.mh_enrolled_pct": (0, 100),
    "conditions.serious_mh_pct": (0, 100),
    "conditions.alcohol_use_pct": (0, 100),
    "conditions.opioid_use_pct": (0, 100),
    "conditions.pulmonary_pct": (0, 100),
    "conditions.cardiovascular_pct": (0, 100),
    "conditions.neurologic_pct": (0, 100),
    "conditions.endocrine_pct": (0, 100),
    "conditions.renal_pct": (0, 100),
    "conditions.malignancy_pct": (0, 100),
    "conditions.hepatitis_pct": (0, 100),
    "conditions.hiv_pct": (0, 100),
}


def _get_inner(data: dict, dotted: str) -> Any:
    """Resolve a dotted key like ``\"census_los.average_daily_census\"``
    through nested dicts."""
    parts = dotted.split(".")
    current: Any = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _semantic_violations(data: dict) -> list[str]:
    """Return a list of human-readable strings for every semantic
    bound violation found in *data*."""
    violations: list[str] = []
    modules = data.get("modules", {})
    if not isinstance(modules, dict):
        violations.append("data.modules is missing or not a dict")
        return violations

    for key, (lo, hi) in SEMANTIC_BOUNDS.items():
        val = _get_inner({"modules": modules}, key)
        if val is None:
            continue  # field absent — schema validation catches this
        try:
            fval = float(val)
        except (TypeError, ValueError):
            violations.append(f"{key}: value {val!r} is not numeric")
            continue
        if math.isnan(fval):
            violations.append(f"{key}: value is NaN")
            continue
        if fval < lo or fval > hi:
            violations.append(
                f"{key}: {fval} is outside expected range [{lo}, {hi}]"
            )
    return violations


def _modules_confidence(modules: dict) -> float:
    """Average of per-module confidence scores (0.0 if none found)."""
    scores = []
    for mod_name in ("census_los", "age_distribution", "homeless",
                     "medicaid", "conditions"):
        mod = modules.get(mod_name)
        if isinstance(mod, dict):
            c = mod.get("confidence")
            if isinstance(c, (int, float)):
                scores.append(float(c))
    return sum(scores) / len(scores) if scores else 0.0


def validate_patient_profile(data: dict) -> tuple[bool, list[str], float]:
    """Validate extracted data from a Patient Profile PDF.

    Runs two layers of validation:

    1. **Schema validation** — ensures *data* can be serialised into a
       ``PatientProfileResult`` Pydantic model.
    2. **Semantic validation** — checks numeric fields fall inside
       reasonable bounds (e.g. percentages 0–100, ADC 0–20000).

    The overall **confidence score** is computed as:

    ``model_confidence × schema_pass × semantic_pass``

    where *schema_pass* and *semantic_pass* are ``1.0`` if the
    respective check passed and ``0.0`` otherwise.

    Parameters
    ----------
    data:
        Parsed JSON dict from the Vision extraction.

    Returns
    -------
    tuple[bool, list[str], float]
        ``(is_valid, error_messages, confidence_score)``.
        ``is_valid`` is ``True`` only when both schema and semantic
        checks pass.
    """
    errors: list[str] = []

    # ── 1. Schema validation ─────────────────────────────────────
    schema_pass = 1.0
    # Build a minimal dict that PatientProfileResult can accept
    try:
        PatientProfileResult(
            document_id=data.get("document_id", "unknown"),
            report_month=data.get("report_month", ""),
            processed_at=data.get(
                "processed_at",
                datetime.now(timezone.utc).isoformat(),
            ),
            modules=data.get("modules", {}),
        )
    except ValidationError as exc:
        for err in exc.errors():
            loc = " → ".join(str(p) for p in err["loc"])
            errors.append(f"schema.{loc}: {err['msg']}")
        schema_pass = 0.0

    # ── 2. Semantic validation ───────────────────────────────────
    semantic_pass = 1.0
    sem_errors = _semantic_violations(data)
    if sem_errors:
        errors.extend(sem_errors)
        semantic_pass = 0.0

    # ── 3. Confidence scoring ────────────────────────────────────
    modules = data.get("modules", {})
    per_module_conf = _modules_confidence(modules)

    # Use top-level confidence from data if present, else module avg
    top_conf = data.get("confidence")
    model_conf = (
        float(top_conf) if isinstance(top_conf, (int, float)) else per_module_conf
    )

    confidence = model_conf * schema_pass * semantic_pass

    is_valid = schema_pass > 0.0 and semantic_pass > 0.0
    return is_valid, errors, confidence


# ── Access Report Validation ──────────────────────────────────────────


FACILITY_CODE_RE = re.compile(r"^[A-Z]{4}$")


def validate_access_report(data: dict) -> tuple[bool, list[str], float]:
    """Validate extracted data from an Access Report PDF.

    Checks
    ------
    1. Report period is present and non-empty.
    2. At least one page classified as summary or facility.
    3. Each facility has a valid 4-letter uppercase code.
    4. Each facility has a non-empty metrics list.
    5. Confidence is the average of per-page confidences.

    Parameters
    ----------
    data:
        Parsed result dict from ``parse_access_report``.

    Returns
    -------
    tuple[bool, list[str], float]
        ``(is_valid, errors, confidence)``.
    """
    errors: list[str] = []

    report_period = data.get("report_period", "")
    if not report_period:
        errors.append("report_period is missing or empty")

    report_type = data.get("report_type", "monthly")
    if report_type not in ("monthly", "quarterly"):
        errors.append(f"report_type must be 'monthly' or 'quarterly', got {report_type!r}")

    summary = data.get("summary")
    facilities = data.get("facilities", [])
    model_runs = data.get("model_runs", [])

    if summary is None and not facilities:
        errors.append("No summary or facility pages found — at least one required")

    if summary is not None:
        summary_metrics = summary.get("metrics", [])
        if not summary_metrics:
            errors.append("Summary page has no metrics extracted")
        for m in summary_metrics:
            if not m.get("metric_name"):
                errors.append("Summary metric missing metric_name")

    seen_codes: set[str] = set()
    for fac in facilities:
        code = fac.get("facility_code", "")
        if not FACILITY_CODE_RE.match(code):
            errors.append(
                f"Invalid facility_code {code!r} — must be 4 uppercase letters"
            )
        if code in seen_codes:
            errors.append(f"Duplicate facility_code {code!r}")
        seen_codes.add(code)

        metrics = fac.get("metrics", [])
        if not metrics:
            errors.append(f"Facility {code} has no metrics")
        for m in metrics:
            if not m.get("metric_name"):
                errors.append(f"Facility {code} metric missing metric_name")

    # Compute confidence as average of per-page confidences
    confidences: list[float] = []
    for run in model_runs:
        c = run.get("confidence")
        if isinstance(c, (int, float)):
            confidences.append(float(c))

    confidence = sum(confidences) / len(confidences) if confidences else 0.0

    is_valid = len(errors) == 0
    return is_valid, errors, confidence
