"""Analyze AR page structure by checking image properties."""
import os

samples_dir = r'C:\tmp\ar-inspect'

for name in sorted(os.listdir(samples_dir)):
    d = os.path.join(samples_dir, name)
    if not os.path.isdir(d):
        continue
    pages = sorted(os.listdir(d))
    print(f'=== {name} ({len(pages)} pages) ===')
    # Check first 8 pages and last 3
    for p in pages[:8]:
        img_path = os.path.join(d, p)
        size_kb = os.path.getsize(img_path) // 1024
        print(f'  {p}: {size_kb}KB')
    if len(pages) > 8:
        print(f'  ... ({len(pages) - 11} more pages) ...')
    for p in pages[-3:]:
        img_path = os.path.join(d, p)
        size_kb = os.path.getsize(img_path) // 1024
        print(f'  {p}: {size_kb}KB')
    print()
