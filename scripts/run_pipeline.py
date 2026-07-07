#!/usr/bin/env python3
"""CLI entry point for the CHS extraction pipeline.

Usage
-----
    python scripts/run_pipeline.py <pdf_path> \
        [--type patient_profile|access_report] \
        [--provider gemini|bedrock] \
        [--output-dir data/output]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the repo root and src/ are on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
for p in (_SRC, _REPO_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chs_pipeline.runner import process_patient_profile, process_access_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract structured data from a CHS PDF.",
    )
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to the PDF file.",
    )
    parser.add_argument(
        "--type",
        type=str,
        default="patient_profile",
        choices=("patient_profile", "access_report"),
        help="PDF type (default: patient_profile).",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="gemini",
        choices=("gemini", "bedrock"),
        help="Vision AI backend to use (default: gemini).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/output",
        help="Root output directory (default: data/output).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.is_file():
        print(f"❌ File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔍 Processing: {pdf_path}")
    print(f"   Type:       {args.type}")
    print(f"   Provider:   {args.provider}")
    print(f"   Output dir: {output_dir.resolve()}")
    print()

    try:
        if args.type == "access_report":
            result = process_access_report(
                pdf_path=str(pdf_path),
                output_dir=str(output_dir),
                provider=args.provider,
            )
        else:
            result = process_patient_profile(
                pdf_path=str(pdf_path),
                output_dir=str(output_dir),
                provider=args.provider,
            )
    except Exception as exc:
        print(f"❌ Pipeline failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # ── Print summary ────────────────────────────────────────────
    document_id = result.get("document_id", "?")
    confidence = result.get("confidence", 0.0)

    print(f"✅  Complete — {document_id}")
    print(f"   Confidence:      {confidence:.3f}")

    if args.type == "access_report":
        summary = result.get("summary")
        facilities = result.get("facilities", [])
        report_period = result.get("report_period", "?")
        report_type = result.get("report_type", "?")
        print(f"   Report period:   {report_period}")
        print(f"   Report type:     {report_type}")
        print(f"   Summary page:    {'✓' if summary else '—'}")
        print(f"   Facilities:      {len(facilities)}")
        for f in facilities:
            fc = f.get("facility_code", "?")
            nm = len(f.get("metrics", []))
            print(f"     • {fc}: {nm} metrics")
    else:
        report_month = result.get("report_month", "?")
        is_valid = result.get("model_run", {}).get("validated", False)
        errors = result.get("model_run", {}).get("validation_errors", [])
        print(f"   Report month:    {report_month}")
        print(f"   Validation:      {'PASSED' if is_valid else 'FAILED'}")
        if errors:
            print(f"   Issues ({len(errors)}):")
            for err in errors:
                print(f"     • {err}")

    doc_out = output_dir / document_id
    print(f"   Result JSON:     {doc_out / 'result.json'}")
    print(f"   Review flags:    {doc_out / 'review_flags.json'}")

    sys.exit(0)


if __name__ == "__main__":
    main()
