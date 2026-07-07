"""Vision-based extraction for CHS Patient Profile PDFs.

Sends a rendered PNG page to Vision AI (Gemini via agy, or Bedrock)
and returns structured JSON matching the PatientProfileResult schema.
"""

import json
import re
from pathlib import Path

from src.chs_pipeline.agy_utils import call_agy


def _read_prompt(prompt_path: str) -> str:
    """Read the extraction prompt from the prompts directory."""
    return Path(prompt_path).read_text(encoding="utf-8").strip()


def _call_gemini(image_path: str, prompt: str) -> str | None:
    """Call Gemini via the agy binary with the prompt and image."""
    full_prompt = (
        f"Look at the image at {image_path}. This is a CHS Patient Profile PDF "
        f"for the NYC Jail System.\n\n{prompt}"
    )
    return call_agy(full_prompt)


def _call_bedrock(image_path: str, prompt: str) -> str | None:
    """Call Amazon Bedrock for Vision extraction. (stub)"""
    _ = image_path, prompt
    raise NotImplementedError("Bedrock provider is not yet implemented")


def _parse_json(text: str) -> dict | None:
    """Parse the first valid JSON object from model output text.

    Handles models that wrap JSON in markdown code fences or extra text.
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


def parse_patient_profile(
    image_path: str,
    prompt_path: str = "prompts/pp_extract_v1.txt",
    provider: str = "gemini",
) -> dict:
    """Send a rendered PNG page to Vision AI and return structured JSON.

    Parameters
    ----------
    image_path:
        Path to the PNG image of the rendered PDF page.
    prompt_path:
        Path to the extraction prompt text file.
    provider:
        Vision AI backend: "gemini" (default) or "bedrock" (stub).

    Returns
    -------
    dict
        Parsed JSON data. Empty dict if parsing fails.
    """
    prompt = _read_prompt(prompt_path)

    if provider == "gemini":
        raw_output = _call_gemini(image_path, prompt)
    elif provider == "bedrock":
        raw_output = _call_bedrock(image_path, prompt)
    else:
        raise ValueError(f"Unknown provider: {provider!r}")

    if raw_output is None:
        return {}

    parsed = _parse_json(raw_output)
    return parsed if parsed is not None else {}
