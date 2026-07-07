"""Inspect page structure of AR samples."""
import json
with open('/tmp/ar-inspect/summary.json') as f:
    data = json.load(f)
for name, info in data.items():
    imgs = info['images']
    print(f'=== {name} ({info["pages"]} pages) ===')
    for i, img in enumerate(imgs):
        print(f'  Page {i+1}: {img}')
    print()
