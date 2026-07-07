"""Vision-based extraction for CHS Access Report PDFs.

Sends rendered PNG pages (one per PDF page) to Vision AI and returns
structured JSON matching the AccessReportResult schema.  Handles
multi-page documents where pages may be summary pages or facility-specific
pages.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


def _read_prompt(prompt_path: str) -> str:
    """Read the extraction prompt from the prompts directory."""
    return Path(prompt_path).read_text(encoding="utf-8").strip()


def _call_agy(image_path: str, prompt: str) -> str | None:
    """Call Gemini via the agy binary with the prompt and image."""
    from src.chs_pipeline.agy_utils import call_agy

    full_prompt = (
        f"Look at the image at {image_path}. This is a page from a CHS "
        f"Access Report for the NYC Jail System.\n\n{prompt}"
    )

    return call_agy(full_prompt)


def _call_bedrock(image_path: str, prompt: str) -> str | None:
    """Call Amazon Bedrock (Claude / Nova) for Vision extraction.

    .. note:: This is a stub for future use.
    """
    raise NotImplementedError("Bedrock provider is not yet implemented.")


def _parse_json(text: str) -> dict | None:
    """Parse the first valid JSON object from model output text.

    Handles models that wrap the JSON in markdown code fences or
    include extra commentary.
    """
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    cleaned = re.sub(
        r"(?s)^(?:```(?:json)?\s*|\s*```\s*$)", "", text
    ).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find outermost JSON object with regex
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None


def _extract_page(
    image_path: str,
    prompt: str,
    provider: str,
    page_number: int,
) -> dict:
    """Send a single page image to Vision AI and return parsed JSON.

    Returns an empty dict if the call or parsing fails.
    """
    if provider == "gemini":
        raw_output = _call_agy(image_path, prompt)
    elif provider == "bedrock":
        raw_output = _call_bedrock(image_path, prompt)
    else:
        raise ValueError(f"Unknown provider: {provider!r}")

    if raw_output is None:
        return {"page_type": "other", "page_number": page_number}

    parsed = _parse_json(raw_output)
    if parsed is None:
        return {"page_type": "other", "page_number": page_number}

    parsed["page_number"] = page_number
    return parsed


def parse_access_report(
    image_paths: list[str],
    prompt_path: str = "prompts/ar_extract_v1.txt",
    provider: str = "gemini",
) -> dict:
    """Process a multi-page Access Report PDF.

    Parameters
    ----------
    image_paths:
        List of paths to rendered PNG images, one per PDF page, in order.
    prompt_path:
        Path to the extraction prompt text file.
    provider:
        Vision AI backend to use (``"gemini"`` or ``"bedrock"``).

    Returns
    -------
    dict
        Aggregated result with structure::

            {
                "report_period": str,       # e.g. "2026-04" or "2025-Q2"
                "report_type": str,         # "monthly" or "quarterly"
                "summary": dict | None,     # citywide metrics if found
                "facilities": list[dict],   # per-facility entries
                "model_runs": list[dict],   # raw page-level results
                "confidence": float,        # average page confidence
            }
    """
    prompt = _read_prompt(prompt_path)

    summary: dict | None = None
    facilities: list[dict] = []
    model_runs: list[dict] = []
    confidences: list[float] = []

    for i, img_path in enumerate(image_paths, start=1):
        page_data = _extract_page(
            image_path=img_path,
            prompt=prompt,
            provider=provider,
            page_number=i,
        )
        model_runs.append(page_data)
        page_conf = page_data.get("confidence")
        if isinstance(page_conf, (int, float)):
            confidences.append(float(page_conf))

        page_type = page_data.get("page_type", "other")

        if page_type == "summary":
            # First summary page wins (citywide)
            if summary is None:
                summary = {
                    "page_number": i,
                    "metrics": page_data.get("metrics", []),
                }
        elif page_type == "facility":
            facility_code = page_data.get("facility_code", "")
            if facility_code:
                facilities.append({
                    "facility_code": facility_code,
                    "page_number": i,
                    "metrics": page_data.get("metrics", []),
                })

    # Determine report period and type from the first page or filename
    report_period = ""
    report_type = "monthly"
    if image_paths:
        # Try extracting from the directory/file name
        first_page = model_runs[0] if model_runs else {}
        report_period = first_page.get("report_period", "")

    confidence = (
        sum(confidences) / len(confidences) if confidences else 0.0
    )

    return {
        "report_period": report_period,
        "report_type": report_type,
        "summary": summary,
        "facilities": facilities,
        "model_runs": model_runs,
        "confidence": confidence,
    }
