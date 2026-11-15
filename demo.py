#!/usr/bin/env python3
"""Brand demo kit: ONE brand per repo. Fill the brand/ folder, then build a ready-to-send demo zip
(3 posts, carousel, Reel, captions, hashtags).

  python demo.py check                  list what is missing in brand/
  python demo.py build                  make output/<brand>_demo_<time>.zip
      --brand path/to/folder            use another brand folder (default: brand/)
      --voice none|edge|elevenlabs      Reel voice (default none: text + animation, optional music in assets/music)
      --character                       Character style for images/AI (default: realistic)
      --no-reel   --offline             skip the Reel / skip the AI and use hand-written or template copy
"""
import argparse
import json
import sys
import time
import zipfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from kit.common import Brand, ROOT  # noqa: E402
from kit import copy as C, posts as P, reel as R  # noqa: E402


def contact_sheet(files, out):
    ims = [Image.open(f).convert("RGB") for f in files]
    w = 360
    ims = [i.resize((w, int(i.height * w / i.width))) for i in ims]
    cols = 4
    rows = (len(ims) + cols - 1) // cols
    rh = max(i.height for i in ims)
    sheet = Image.new("RGB", (cols * w, rows * rh), (245, 245, 245))
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % cols) * w, (k // cols) * rh))
    sheet.save(out, quality=88)


def build(brand_dir=None, voice="none", reel=True, offline=False, character="realistic"):
    b = Brand(brand_dir)
    slug = b.slug
    stamp = time.strftime("%Y%m%d_%H%M")
    probs = b.problems()
    for p_ in probs:
        print("WARNING:", p_)
    out = ROOT / "output" / f"{slug}_demo_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    
    # character पॅरामीटर AI ला पास करा
    copy, how = C.make_copy(b, use_ai=not offline, character=character)
    
    print("Copy:", how)
    (out / "copy.json").write_text(json.dumps(copy, ensure_ascii=False, indent=1), encoding="utf-8")
    files = []
    for i, p in enumerate(copy["posts"][:3], 1):
        f = out / f"post_{i}_{p.get('kind', 'hero')}.jpg"
        P.post(b, p).save(f, quality=93)
        files.append(f)
    for i, im in enumerate(P.carousel(b, copy["carousel"]), 1):
        f = out / f"carousel_{i}.jpg"
        im.save(f, quality=93)
        files.append(f)
    reel_note = "not made"
    if reel:
        total, reel_note = R.build_reel(b, copy["reel"], out / "reel.mp4", voice=voice)
        reel_note = f"{total:.0f}s, {reel_note}"
    cap = copy["captions"]
    tags = " ".join(copy.get("hashtags", []))
    names = {"post_1": "Post 1", "post_2": "Post 2", "post_3": "Post 3", "carousel": "Carousel", "reel": "Reel"}
    txt = "\n\n".join(f"=== {names[k]} ===\n{cap.get(k, '')}\n\n{tags}" for k in names)
    (out / "captions_and_hashtags.txt").write_text(txt, encoding="utf-8")
    warns = C.checks(copy, b)
    note = [f"CHECK BEFORE SENDING THIS DEMO TO {b.name.upper()}", "", f"Copy: {how}", f"Reel: {reel_note}", ""]
    note += warns or ["No automatic warnings."]
    note += ["", "Always check by eye: logo and colours, spelling (especially Hindi, Bengali, Marathi), phone number, product image quality,",
             "every claim and number against what the client gave you. This is a demo: do not post it on the client's page without their approval.",
             "Use the client's logo and product images only for this client."]
    (out / "CHECK_BEFORE_SENDING.txt").write_text("\n".join(note), encoding="utf-8")
    contact_sheet(files, out / "preview.jpg")
    zp = ROOT / "output" / f"{slug}_demo_{stamp}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.iterdir()):
            z.write(f, f"{slug}_demo/{f.name}")
    print("Done:", zp)
    for w in warns:
        print(" ", w)
    return zp


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--brand", default=None)
    bd = sub.add_parser("build")
    bd.add_argument("--brand", default=None)
    bd.add_argument("--voice", default="none", choices=["none", "edge", "elevenlabs"])
    
    # --character आर्ग्युमेंट जोडा
    bd.add_argument("--character", default="realistic", help="Set character style for AI images (default: realistic)")
    
    bd.add_argument("--no-reel", action="store_true")
    bd.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    if a.cmd == "check":
        b = Brand(a.brand)
        probs = b.problems()
        print(f"Brand: {b.name}  ({len(b.products)} products)")
        print("\n".join("  - " + p for p in probs) if probs else "Everything needed is there.")
    else:
        # build फंक्शनला a.character पास करा
        build(a.brand, a.voice, not a.no_reel, a.offline, a.character)


if __name__ == "__main__":
    main()
