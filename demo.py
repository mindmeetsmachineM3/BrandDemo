#!/usr/bin/env python3
"""Brand demo kit: ONE brand per repo. Fill the brand/ folder, then build a ready-to-send demo zip
(3 posts, carousel, Reel, captions, hashtags).

  python demo.py check                  list what is missing in brand/
  python demo.py build                  make output/<brand>_demo_<time>.zip
      --brand path/to/folder            use another brand folder (default: brand/)
      --voice auto|none|edge|elevenlabs Reel voice (default auto: ElevenLabs if keys exist, else free edge voice; background beat is generated, or put mp3s in assets/music)
      --no-reel   --offline             skip the Reel / skip the AI and use hand-written or template copy
"""
import argparse
import os
import json
import sys
import time
import zipfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from kit.common import Brand, ROOT  # noqa: E402
from kit import copy as C, posts as P, reel as R, theme as TH  # noqa: E402
import random  # noqa: E402


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


HIST = ROOT / "output" / "history.json"


def load_hist():
    try:
        return json.loads(HIST.read_text(encoding="utf-8"))
    except Exception:
        return {"moods": [], "lines": []}


def build(brand_dir=None, voice="auto", reel=True, offline=False, seed=None, chars="auto", reel_style="auto"):
    presenter_err = ""
    b = Brand(brand_dir)
    slug = b.slug
    stamp = time.strftime("%Y%m%d_%H%M")
    seed = seed if seed is not None else random.SystemRandom().randrange(1 << 30)
    rng = random.Random(seed)
    hist = load_hist()
    probs = b.problems()
    for p_ in probs:
        print("WARNING:", p_)
    out = ROOT / "output" / f"{slug}_demo_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    copy, how = C.make_copy(b, use_ai=not offline, rng=rng, avoid=hist["lines"])
    print("Copy:", how, "| seed", seed)
    (out / "copy.json").write_text(json.dumps(copy, ensure_ascii=False, indent=1), encoding="utf-8")
    # 5 pieces (3 posts, carousel, reel), every one with its own colour mood, display font, pattern and characters
    ths = TH.plan(5, b.primary, seed=seed, avoid_moods=hist["moods"][-8:], chars="human", industry=b.d.get("industry", ""))
    if chars == "auto":
        chars = "photo" if (os.getenv("GEMINI_API_KEY") and not offline) else "human"
    if chars == "photo":
        for t in ths:
            t.chars = "photo"
    elif chars == "blob":
        for t in ths:
            t.chars = "blob"
    elif chars == "mix":
        for k, t in enumerate(ths):
            t.chars = "human" if k % 2 == 0 else "blob"
    kinds = rng.sample(P.KINDS, 3)
    by_kind = {p["kind"]: p for p in copy["posts"]}
    files = []
    look = []
    for i, kind in enumerate(kinds, 1):
        t = ths[i - 1]
        f = out / f"post_{i}_{kind}.jpg"
        P.post(b, by_kind[kind], t, random.Random(t.seed), kind).save(f, quality=93)
        files.append(f)
        look.append(f"Post {i} ({kind}): {t.mood}, font {t.font}, {t.person['role'] if t.chars == 'human' else 'blob mascot'}")
    for i, im in enumerate(P.carousel(b, copy["carousel"], [ths[3]], [random.Random(ths[3].seed)]), 1):
        f = out / f"carousel_{i}.jpg"
        im.save(f, quality=93)
        files.append(f)
    look.append(f"Carousel: {ths[3].mood}, font {ths[3].font}, {ths[3].person['role'] if ths[3].chars == 'human' else 'blob mascot'}")
    reel_note = "not made"
    if reel:
        total, reel_note = None, None
        if reel_style in ("auto", "presenter") and os.getenv("GEMINI_API_KEY") and not offline:
            try:
                from kit import presenter as PR
                total, reel_note = PR.build(b, ths[4], copy["reel"], out / "reel.mp4")
            except Exception as ex:
                print("REALISTIC PRESENTER REEL FAILED, making the animated Reel instead:", str(ex)[:300], file=sys.stderr)
                presenter_err = str(ex)[:200]
        if total is None:
            total, reel_note = R.build_reel(b, copy["reel"], out / "reel.mp4", ths[4], voice=voice)
        reel_note = f"{total:.0f}s, {reel_note}"
    look.append(f"Reel: {ths[4].mood}, font {ths[4].font}, {ths[4].person['role'] if ths[4].chars == 'human' else 'blob mascot'}")
    hist["moods"] = (hist["moods"] + [t.mood for t in ths])[-30:]
    hist["lines"] = (hist["lines"] + C.lines_used(copy))[-80:]
    HIST.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    cap = copy["captions"]
    tags = " ".join(copy.get("hashtags", []))
    names = {f"post_{i}": (f"Post {i}", kinds[i - 1]) for i in (1, 2, 3)}
    names.update({"carousel": ("Carousel", "carousel"), "reel": ("Reel", "reel")})
    txt = "\n\n".join(f"=== {nm} ===\n{cap.get(ck, '')}\n\n{tags}" for _, (nm, ck) in names.items())
    txt += "\n\n(Looks used: " + "; ".join(look) + ")"
    (out / "captions_and_hashtags.txt").write_text(txt, encoding="utf-8")
    warns = C.checks(copy, b)
    note = [f"CHECK BEFORE SENDING THIS DEMO TO {b.name.upper()}", "", f"Copy: {how}", f"Reel: {reel_note}", ""]
    note += warns or ["No automatic warnings."]
    from kit import photo as _ph
    if _ph.FAILED:
        note += ["", "WARNING: realistic photo people could NOT be generated (" + _ph.FAILED[0][:120] + "), so the posts show ILLUSTRATED people. Fix the Gemini image access and run again before sending."]
    if presenter_err:
        note += ["", "WARNING: the realistic talking-person Reel failed (" + presenter_err + "), so you got the animated Reel. Fix the video access and run again before sending."]
    note += ["", "Always check by eye: logo and colours, spelling (especially Hindi, Bengali, Marathi), phone number, product image quality,",
             "every claim and number against what the client gave you. This is a demo: do not post it on the client's page without their approval.",
             "Use the client's logo and product images only for this client."]
    if chars == "photo":
        note += ["", "The people in these pictures are AI-generated (fictional, carry an invisible SynthID watermark). Tell the client so, check faces and hands for",
                 "errors, and regenerate (run again) if any person looks odd. Do not use them to imply a real customer or endorsement."]
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
    bd.add_argument("--voice", default="auto", choices=["auto", "none", "edge", "elevenlabs"], help="auto = ElevenLabs if keys exist, else free edge voice")
    bd.add_argument("--no-reel", action="store_true")
    bd.add_argument("--reel-style", default="auto", choices=["auto", "presenter", "animated"], help="presenter = realistic AI person speaking (Gemini Omni video); animated = graphics Reel; auto = presenter when the key allows")
    bd.add_argument("--offline", action="store_true")
    bd.add_argument("--seed", type=int, default=None, help="repeat an earlier look (printed in the log)")
    bd.add_argument("--chars", default="auto", choices=["auto", "photo", "human", "blob", "mix"], help="auto = photo-real AI people when GEMINI_API_KEY exists, else illustrated people; photo; human = illustrated; blob; mix")
    a = ap.parse_args()
    if a.cmd == "check":
        b = Brand(a.brand)
        probs = b.problems()
        print(f"Brand: {b.name}  ({len(b.products)} products)")
        print("\n".join("  - " + p for p in probs) if probs else "Everything needed is there.")
    else:
        build(a.brand, a.voice, not a.no_reel, a.offline, a.seed, a.chars, a.reel_style)


if __name__ == "__main__":
    main()
