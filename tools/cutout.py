#!/usr/bin/env python3
"""Make a transparent PNG from a pack shot on a plain background.   python tools/cutout.py in.jpg out.png
(demo.py also does this automatically when a product image has no transparency.)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kit.common import auto_cutout  # noqa: E402
from PIL import Image  # noqa: E402

if len(sys.argv) != 3:
    raise SystemExit(__doc__)
auto_cutout(Image.open(sys.argv[1]).convert("RGBA")).save(sys.argv[2])
print("saved", sys.argv[2], "- open it on a coloured background and check the edges")
