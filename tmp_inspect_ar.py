"""Render and inspect AR samples."""
from src.chs_pipeline.render import render_pages
import os, json

samples = [
    'data/raw/access_reports/2026-04.pdf',
    'data/raw/access_reports/2025-Q2.pdf',
    'data/raw/access_reports/2024-Q1.pdf',
    'data/raw/access_reports/2022-Q3.pdf',
    'data/raw/access_reports/2019-03.pdf',
]

results = {}
for s in samples:
    name = os.path.basename(s).replace('.pdf','')
    out = f'/tmp/ar-inspect/{name}'
    os.makedirs(out, exist_ok=True)
    imgs = render_pages(s, out, dpi=200)
    results[name] = {
        'pages': len(imgs),
        'images': imgs,
    }
    print(f'{name}: {len(imgs)} pages')

with open('/tmp/ar-inspect/summary.json','w') as f:
    json.dump(results, f, indent=2)
