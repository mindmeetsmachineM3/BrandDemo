"""Turn the plain-text brief (brand/prompt.txt) into the structured brand profile. Needs GEMINI_API_KEY.
Colours come from the brief if given, otherwise they are read from the logo."""
import colorsys
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from . import copy as C

PROFILE_PROMPT = """Read the brand brief below and extract a structured brand profile. Use ONLY facts written in the brief. If something is not given, leave it empty ("" or []), never invent prices, offers, phone numbers, awards or claims.

BRIEF:
{brief}

PRODUCT IMAGE FILES available (file names): {files}
Match each product in the brief to one of these files (by name or by order). If the brief names no products, make one product per file using a plain name taken from the file name.

Return ONLY JSON in this shape:
{{"name":"","handle":"instagram handle without @","phone":"","tagline":"",
 "language":"english|hinglish|hindi|marathi|bengali (the language the posts should be written in; default english)",
 "industry":"","audience":"","tone":"",
 "colors":{{"primary":"#hex or empty","secondary":"#hex or empty","dark":"#hex or empty","light":"#hex or empty"}},
 "post_ratio":"4:5 or 1:1 (default 4:5)",
 "products":[{{"id":"short_snake_case","name":"","image":"exact file name from the list","description":"one line","usps":["real benefit stated in the brief"]}}],
 "offers":[],"dates":[],"do":[],"dont":[],"extra_prompt":"any special request from the brief, in one or two sentences"}}"""


def logo_palette(path):
    """primary / secondary / dark / light guessed from the logo pixels."""
    try:
        im = Image.open(path).convert("RGBA").resize((120, 120))
    except Exception:
        return {}
    a = np.asarray(im).reshape(-1, 4)
    a = a[a[:, 3] > 200][:, :3].astype(int)
    if not len(a):
        return {}
    mx, mn = a.max(1), a.min(1)
    sat = (mx - mn)
    colored = a[(sat > 60) & (mx > 60)]
    q = (colored // 32) * 32 if len(colored) else None

    def hx(c):
        return "#%02X%02X%02X" % tuple(int(v) for v in c)

    if q is None or not len(q):
        return {"primary": "#1F6FEB", "secondary": "#FFC83D", "dark": "#111827", "light": "#F7F8FA"}
    vals, counts = np.unique(q, axis=0, return_counts=True)
    order = np.argsort(-counts)
    prim = vals[order[0]] + 16
    sec = None
    for i in order[1:]:
        c = vals[i] + 16
        hp = colorsys.rgb_to_hsv(*(prim / 255))[0]
        hc = colorsys.rgb_to_hsv(*(c / 255))[0]
        dh = min(abs(hp - hc), 1 - abs(hp - hc))
        if dh > 0.08 and counts[i] > 0.05 * counts.sum() and (c.max() - c.min()) > 110:
            sec = c
            break
    if sec is None:                                   # no second brand colour in the logo: a warm accent (or navy if the brand is already yellow)
        warm = prim[0] > 200 and prim[1] > 150 and prim[2] < 110
        sec = np.array([16, 40, 110]) if warm else np.array([255, 200, 61])
    dark = (prim * 0.18).astype(int)
    return {"primary": hx(prim), "secondary": hx(sec), "dark": hx(dark), "light": "#F7F8FA"}


def build_profile(bdir, brief):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise SystemExit("brand/prompt.txt needs GEMINI_API_KEY to be read. Add the secret, or write brand/brand.json by hand.")
    pdir = Path(bdir) / "assets" / "products"
    files = sorted(f.name for f in pdir.glob("*") if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
    models = [m for m in (os.getenv("DEMO_MODELS") or "gemini-3.7-flash,gemini-2.5-flash,gemini-3.6-flash,gemini-3.5-flash").split(",") if m]
    prof = C._call(PROFILE_PROMPT.format(brief=brief, files=", ".join(files) or "(none)"), models, key)
    prof.setdefault("products", [])
    have = {p.get("image") for p in prof["products"]}
    for f in files:                                   # every image becomes a product, even if the model skipped it
        if f not in have:
            nm = re.sub(r"[_\-]+", " ", Path(f).stem).title()
            prof["products"].append({"id": re.sub(r"\W+", "_", Path(f).stem.lower()), "name": nm, "image": f, "description": "", "usps": []})
    prof["products"] = [p for p in prof["products"] if p.get("image") in files]
    ids = set()
    for p in prof["products"]:
        p["id"] = re.sub(r"\W+", "_", (p.get("id") or Path(p["image"]).stem).lower())
        while p["id"] in ids:
            p["id"] += "_2"
        ids.add(p["id"])
    col = {k: v for k, v in (prof.get("colors") or {}).items() if isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v)}
    guess = logo_palette(Path(bdir) / "assets" / "logo.png")
    prof["colors"] = {**guess, **col}
    prof["language"] = (prof.get("language") or "english").lower()
    if prof["language"] not in C.LANG_NOTE:
        prof["language"] = "english"
    prof["post_ratio"] = prof.get("post_ratio") if prof.get("post_ratio") in ("4:5", "1:1") else "4:5"
    prof.setdefault("dont", [])
    prof["dont"] += ["No cartoon or film characters", "No public figures"]
    return prof
