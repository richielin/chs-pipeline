#!/usr/bin/env python3
"""Debug 2026-05 rendering."""
import sys, os
sys.path.insert(0, "src")
sys.path.insert(0, ".")
from chs_pipeline.render import render_pages

paths = render_pages("data/raw/patient_profiles/2026-05.pdf", "data/output/2026-05/debug_rendered", dpi=250)
for p in paths:
    print(p, os.path.getsize(p) if os.path.exists(p) else "not found")
