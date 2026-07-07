#!/usr/bin/env python3
"""Run curation on the output directory and print the CSV path."""
from chs_pipeline.curate import curate_patient_profile
import sys

if __name__ == "__main__":
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "data/output"
    csv_path = curate_patient_profile(output_dir)
    print(f"CSV written to: {csv_path}")
