"""Shared utilities for calling agy (Antigravity CLI) with transcript fallback.

agy's --print mode is documented to not reliably return stdout.
This module provides a robust fallback: if stdout is empty, it reads
the model response from agy's conversation transcript files.
"""
import json
import os
import re
import subprocess
from pathlib import Path


AGY_PATH = os.path.expanduser("~/AppData/Local/agy/bin/agy")
BRAIN_DIR = os.path.expanduser("~/.gemini/antigravity-cli/brain")


def _resolve_agy_path() -> str:
    """Find the agy binary (with .exe fallback on Windows)."""
    if os.path.isfile(AGY_PATH):
        return AGY_PATH
    agy_exe = AGY_PATH + ".exe"
    if os.path.isfile(agy_exe):
        return agy_exe
    raise FileNotFoundError(
        f"agy binary not found at {AGY_PATH} (or {agy_exe})."
    )


def _count_brain_dirs_before(path: str) -> set[str]:
    """Get the set of conversation dirs in agy's brain dir."""
    if not os.path.isdir(BRAIN_DIR):
        return set()
    return {d for d in os.listdir(BRAIN_DIR)
            if os.path.isdir(os.path.join(BRAIN_DIR, d))}


def _find_latest_transcript() -> str | None:
    """Find the most recent agy conversation transcript file."""
    if not os.path.isdir(BRAIN_DIR):
        return None
    convs = [d for d in os.listdir(BRAIN_DIR)
             if os.path.isdir(os.path.join(BRAIN_DIR, d))]
    convs.sort(key=lambda d: os.path.getmtime(os.path.join(BRAIN_DIR, d)),
               reverse=True)
    for conv in convs:
        tp = os.path.join(BRAIN_DIR, conv, ".system_generated", "logs",
                          "transcript.jsonl")
        if os.path.isfile(tp):
            return tp
    return None


def _get_new_transcript(before: set[str]) -> str | None:
    """Find a transcript that appeared after the `before` snapshot."""
    after = _count_brain_dirs_before("")
    new_dirs = after - before
    for nd in new_dirs:
        tp = os.path.join(BRAIN_DIR, nd, ".system_generated", "logs",
                          "transcript.jsonl")
        if os.path.isfile(tp):
            return tp
    return None


def _extract_json_from_transcript(transcript_path: str) -> str | None:
    """Extract the last model response containing JSON from a transcript."""
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                role = entry.get("role", "")
                content = entry.get("content", "")
                if role == "model" and content and "{" in content:
                    return content
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return None


def call_agy(prompt: str) -> str | None:
    """Call agy with --print mode, with transcript fallback.

    Returns the model response text, or None on failure.
    """
    agy_path = _resolve_agy_path()
    before = _count_brain_dirs_before("")

    result = subprocess.run(
        [agy_path, "--dangerously-skip-permissions", "--print", prompt],
        capture_output=True,
        text=True,
        timeout=180,
        env={**os.environ},
    )

    # Try stdout first
    output = result.stdout.strip()
    if output:
        return output

    # Fallback: read from transcript
    transcript = _get_new_transcript(before)
    if transcript:
        return _extract_json_from_transcript(transcript)

    # Last resort: try the latest transcript
    latest = _find_latest_transcript()
    if latest:
        return _extract_json_from_transcript(latest)

    return None
