#!/usr/bin/env python3
"""Backfill: process all Patient Profile PDFs in a directory through the pipeline.

Usage
-----
    python scripts/backfill.py \\
        --dir data/raw/patient_profiles \\
        --output-dir data/output \\
        --provider gemini
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure the repo root and src/ are on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
for p in (_SRC, _REPO_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chs_pipeline.runner import process_patient_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill all Patient Profile PDFs through the pipeline.",
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="data/raw/patient_profiles",
        help="Directory containing PDF files (sorted by filename).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/output",
        help="Root output directory for pipeline results.",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="gemini",
        choices=("gemini", "bedrock"),
        help="Vision AI backend to use (default: gemini).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    pdf_dir = Path(args.dir)
    if not pdf_dir.is_dir():
        print(f"❌ Directory not found: {pdf_dir}", file=sys.stderr)
        sys.exit(1)

    # Discover PDFs, sorted by filename
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"❌ No PDFs found in {pdf_dir}", file=sys.stderr)
        sys.exit(1)

    total = len(pdfs)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📂 PDF directory:  {pdf_dir.resolve()}")
    print(f"📁 Output dir:     {output_dir.resolve()}")
    print(f"🤖 Provider:       {args.provider}")
    print(f"📄 PDFs to process: {total}")
    print()

    successes = 0
    failures: list[tuple[Path, str]] = []
    start_time = time.time()

    for i, pdf_path in enumerate(pdfs, 1):
        print(f"[{i:2d}/{total}] Processing: {pdf_path.name} ...", end=" ", flush=True)

        try:
            result = process_patient_profile(
                pdf_path=str(pdf_path),
                output_dir=str(output_dir),
                provider=args.provider,
            )
            is_valid = result.get("model_run", {}).get("validated", False)
            confidence = result.get("confidence", 0.0)
            if is_valid:
                successes += 1
                print(f"✅ PASS (confidence={confidence:.3f})")
            else:
                errors = result.get("model_run", {}).get("validation_errors", [])
                failures.append((pdf_path, "; ".join(errors) if errors else "Validation failed"))
                print(f"⚠️  FAIL (confidence={confidence:.3f})")
                for err in errors[:3]:
                    print(f"       • {err}")
        except Exception as exc:
            failures.append((pdf_path, str(exc)))
            print(f"❌ ERROR: {exc}")

    elapsed = time.time() - start_time
    failed_count = len(failures)

    print()
    print("=" * 60)
    print("BACKFILL COMPLETE")
    print(f"  Total:       {total}")
    print(f"  Succeeded:   {successes}")
    print(f"  Failed:      {failed_count}")
    print(f"  Time taken:  {elapsed:.1f}s ({elapsed / max(total, 1):.1f}s per PDF)")
    if failures:
        print()
        print("  Failures:")
        for pdf_path, reason in failures:
            print(f"    • {pdf_path.name}: {reason}")
    print()

    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
