#!/usr/bin/env python3
"""Check rendered image dimensions."""
from PIL import Image
import os

img = Image.open("data/output/2026-05/rendered/page_0001.png")
print(f"Size: {img.size}")
print(f"Mode: {img.mode}")
print(f"File size: {os.path.getsize('data/output/2026-05/rendered/page_0001.png')} bytes")
