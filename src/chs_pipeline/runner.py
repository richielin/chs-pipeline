"""Orchestrate the Patient Profile pipeline for a single PDF.

``process_patient_profile`` accepts a PDF path, renders it to PNG,
sends the image to Vision AI, validates the result, and persists
structured output to disk.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chs_pipeline.render import render_pages
from chs_pipeline.parse_patient_profile import parse_patient_profile
from chs_pipeline.parse_access_report import parse_access_report
from chs_pipeline.validate import validate_patient_profile, validate_access_report
from chs_pipeline.schemas import PatientProfileResult, AccessReportResult


def process_patient_profile(
    pdf_path: str,
    output_dir: str,
    provider: str = "gemini",
) -> dict:
    """Run the full Patient Profile pipeline on a single PDF.

    Steps
    -----
    1. Render the PDF's first page to a PNG image.
    2. Send the image to the configured Vision AI (``provider``).
    3. Validate the returned data (schema + semantic checks).
    4. Assemble a ``PatientProfileResult`` and persist it as
       ``result.json``.
    5. Write a companion ``review_flags.json`` if validation raised
       warnings.
    6. Return the combined result dict.

    Parameters
    ----------
    pdf_path:
        Path to the CHS Patient Profile PDF.
    output_dir:
        Directory under which a ``<document_id>/`` sub-folder is
        created containing ``result.json``, ``review_flags.json``,
        and a ``rendered/`` directory with the page images.
    provider:
        Vision backend (``"gemini"`` or ``"bedrock"``).

    Returns
    -------
    dict
        Full result dictionary (the same data written to
        ``result.json``).
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    document_id = pdf_path.stem  # e.g. "patient-profile-sample"

    # ── Output paths ─────────────────────────────────────────────
    doc_out = output_dir / document_id
    rendered_dir = doc_out / "rendered"
    rendered_dir.mkdir(parents=True, exist_ok=True)

    result_path = doc_out / "result.json"
    flags_path = doc_out / "review_flags.json"

    # ── 1. Render PDF → PNG ──────────────────────────────────────
    image_paths = render_pages(
        str(pdf_path),
        output_dir=str(rendered_dir),
        dpi=250,
    )

    if not image_paths:
        raise RuntimeError(f"No pages rendered from {pdf_path}")

    first_image = image_paths[0]

    # ── 2. Parse via Vision AI ───────────────────────────────────
    prompt_path = (
        Path(__file__).resolve().parent.parent.parent
        / "prompts"
        / "pp_extract_v1.txt"
    )

    raw_data = parse_patient_profile(
        image_path=first_image,
        prompt_path=str(prompt_path),
        provider=provider,
    )

    # ── 3. Validate ──────────────────────────────────────────────
    is_valid, validation_errors, confidence = validate_patient_profile(raw_data)

    # ── 4. Assemble result ───────────────────────────────────────
    now = datetime.now(timezone.utc)
    report_month = raw_data.get("report_month", now.strftime("%Y-%m"))

    result = PatientProfileResult(
        document_id=document_id,
        source_type="patient_profile",
        report_month=report_month,
        template_version="pp_v1",
        processed_at=now.isoformat(),
        confidence=confidence,
        modules=raw_data.get("modules", {}),
        model_run={
            "provider": provider,
            "validated": is_valid,
            "validation_errors": validation_errors,
            "rendered_pages": image_paths,
        },
    )

    result_dict = result.model_dump()

    # Write result.json
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, indent=2, default=str)

    # ── 5. Write review flags (if validation warnings exist) ─────
    flags: dict[str, Any] = {"needs_review": not is_valid}
    if validation_errors:
        flags["issues"] = validation_errors
    if confidence < 0.5:
        flags.setdefault("issues", []).append(
            f"Low confidence score ({confidence:.3f})"
        )

    with open(flags_path, "w", encoding="utf-8") as f:
        json.dump(flags, f, indent=2)

    return result_dict


def process_access_report(
    pdf_path: str,
    output_dir: str,
    provider: str = "gemini",
) -> dict:
    """Run the full Access Report pipeline on a single PDF.

    Steps
    -----
    1. Render all PDF pages to PNG images.
    2. Send each page image to Vision AI for classification + extraction.
    3. Aggregate summary + facility data.
    4. Validate the result.
    5. Persist as result.json + review_flags.json.

    Returns the combined result dict.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    document_id = pdf_path.stem

    # ── Output paths ─────────────────────────────────────────────
    doc_out = output_dir / document_id
    rendered_dir = doc_out / "rendered"
    rendered_dir.mkdir(parents=True, exist_ok=True)

    result_path = doc_out / "result.json"
    flags_path = doc_out / "review_flags.json"

    # ── 1. Render PDF → PNG ──────────────────────────────────────
    image_paths = render_pages(
        str(pdf_path),
        output_dir=str(rendered_dir),
        dpi=200,
    )

    if not image_paths:
        raise RuntimeError(f"No pages rendered from {pdf_path}")

    # ── 2. Parse via Vision AI ───────────────────────────────────
    prompt_path = (
        Path(__file__).resolve().parent.parent.parent
        / "prompts"
        / "ar_extract_v1.txt"
    )

    raw_data = parse_access_report(
        image_paths=image_paths,
        prompt_path=str(prompt_path),
        provider=provider,
    )

    # ── 3. Validate ──────────────────────────────────────────────
    is_valid, validation_errors, confidence = validate_access_report(raw_data)

    # ── 4. Assemble result ───────────────────────────────────────
    now = datetime.now(timezone.utc)

    result = AccessReportResult(
        document_id=document_id,
        source_type="access_report",
        report_period=raw_data.get("report_period", ""),
        report_type=raw_data.get("report_type", "monthly"),
        template_version="ar_v1",
        processed_at=now.isoformat(),
        confidence=confidence,
        summary=raw_data.get("summary"),
        facilities=raw_data.get("facilities", []),
        model_runs=raw_data.get("model_runs", []),
    )

    result_dict = result.model_dump()

    # Write result.json
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, indent=2, default=str)

    # ── 5. Write review flags ────────────────────────────────────
    flags: dict[str, Any] = {"needs_review": not is_valid}
    if validation_errors:
        flags["issues"] = validation_errors
    if confidence < 0.5:
        flags.setdefault("issues", []).append(
            f"Low confidence score ({confidence:.3f})"
        )

    with open(flags_path, "w", encoding="utf-8") as f:
        json.dump(flags, f, indent=2)

    return result_dict
