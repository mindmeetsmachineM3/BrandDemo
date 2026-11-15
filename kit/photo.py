"""Photo-real people. An image model (Gemini 'Nano Banana', uses GEMINI_API_KEY) generates ORIGINAL ordinary-looking people on a flat green
background; we key the green out and place them in the layouts. The real product image is always composited by us (never redrawn by the AI),
so the pack shot stays exact. Later poses of the same piece get the first photo as a reference so the person stays the same.
Falls back to the illustrated people if the API fails."""
import base64
import io
import os
import sys
import time

import numpy as np
import requests
from PIL import Image, ImageFilter

from .common import ROOT

MODELS = "gemini-3.1-flash-image,gemini-3.1-flash-lite-image,gemini-2.5-flash-image"
CACHE = ROOT / "output" / "people_cache"
POSE_TXT = {"wave": "waving with one hand raised, friendly", "cheer": "both arms raised in joy, celebrating", "point": "one arm stretched out to the side, pointing with the index finger",
            "hold": "both hands held in front of the waist as if presenting something (hands empty)", "shrug": "shrugging with open palms, puzzled",
            "stand": "standing relaxed, arms by the sides"}
EXPR_TXT = {"grin": "big natural smile", "wow": "surprised, mouth open", "sad": "worried, slightly sad", "smirk": "confident half-smile", "wink": "playful wink and smile"}
SKIN = {(247, 214, 184): "light wheatish", (234, 190, 150): "wheatish", (214, 160, 113): "medium brown", (190, 130, 88): "brown", (160, 104, 66): "deep brown", (126, 80, 50): "dark brown"}
ROLE_TXT = {"painter": "house painter in clean work overalls, cap", "homeowner": "homeowner in casual shirt", "designer": "interior designer, smart casual, glasses",
            "shopkeeper": "friendly shopkeeper wearing an apron", "homemaker": "homemaker in a simple kurta or salwar, modest", "student": "college student in t-shirt and jeans",
            "engineer": "site engineer in shirt and safety helmet"}
STYLE_TXT = {"short": "short hair", "side": "side-parted hair", "beard": "short beard", "bun": "hair in a bun", "long": "long hair", "ponytail": "ponytail", "bald": "bald head"}


def chroma(im):
    """flat green background -> transparent, with edge de-spill"""
    a = np.asarray(im.convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    dom = g - np.maximum(r, b)
    alpha = np.clip((70 - dom) / 45.0, 0, 1)                 # dom>=70 fully background, <=25 fully kept
    spill = np.minimum(g, np.maximum(r, b))
    g2 = np.where(dom > 0, spill, g)
    out = np.dstack([r, g2, b, (alpha * 255).astype(int)]).clip(0, 255).astype("uint8")
    im2 = Image.fromarray(out, "RGBA")
    al = im2.split()[3].filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(.8))
    im2.putalpha(al)
    bb = im2.getbbox()
    return im2.crop(bb) if bb else im2


def _prompt(th, pose, expr, ref):
    P = th.person
    skin = SKIN.get(tuple(P["skin"]), "wheatish")
    ident = f"an ordinary adult Indian {ROLE_TXT.get(P['role'], 'person')}, {skin} skin tone, {STYLE_TXT.get(P['style'], 'short hair')}"
    base = (f"Photorealistic full-body photograph of {ident}. Pose: {POSE_TXT.get(pose, POSE_TXT['stand'])}. Expression: {EXPR_TXT.get(expr, 'smile')}. "
            "Natural, candid, professional advertising photo quality, soft studio light, head to toe fully visible with shoes, centered. "
            "Background: one perfectly flat solid pure green (#00FF00) colour, no shadows on the background, no floor, no props. "
            "The person must not wear anything green. No text, no logos, no watermark. This must be a fictional person who does not resemble any real or famous individual.")
    if ref:
        base = "Use the person in the reference image: SAME face, hair, skin tone and clothes. New pose only. " + base
    return base


def _call(prompt, ref_png, key):
    models = [m for m in (os.getenv("IMAGE_MODELS") or MODELS).split(",") if m]
    parts = [{"text": prompt}]
    if ref_png:
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(ref_png).decode()}})
    last = ""
    for m in models:
        for attempt in range(2):
            try:
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                                  headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                                  json={"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}}, timeout=180)
            except Exception as ex:
                last = str(ex)[:120]
                time.sleep(3)
                continue
            if r.ok:
                try:
                    for pt in r.json()["candidates"][0]["content"]["parts"][::-1]:
                        d = pt.get("inline_data") or pt.get("inlineData")
                        if d and not pt.get("thought"):
                            return base64.b64decode(d["data"])
                    last = f"{m}: no image in reply"
                except Exception as ex:
                    last = f"{m}: bad reply ({ex})"
                break
            last = f"{m}: {r.status_code} {r.text[:140]}"
            if r.status_code in (429, 500, 503):
                time.sleep(6 * (attempt + 1))
                continue
            break
    raise RuntimeError(last)


def get(th, pose, expr):
    """RGBA photo person (full size) for this theme's person, pose and expression. Raises on failure."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("no GEMINI_API_KEY")
    CACHE.mkdir(parents=True, exist_ok=True)
    P = th.person
    f = CACHE / f"{th.seed}_{P['role']}_{P['style']}_{pose}_{expr}.png"
    if f.exists():
        return Image.open(f).convert("RGBA")
    ref = getattr(th, "_photo_ref", None)
    raw = _call(_prompt(th, pose, expr, ref), ref, key)
    im = chroma(Image.open(io.BytesIO(raw)))
    if im.width < 50 or im.height < 100:
        raise RuntimeError("generated picture unusable")
    im.save(f)
    if ref is None:
        b = io.BytesIO()
        Image.open(io.BytesIO(raw)).convert("RGB").save(b, "PNG")
        object.__setattr__(th, "_photo_ref", b.getvalue())
    return im


FAILED = []


def sprite(th, w, pose, expr, flip=False):
    im = get(th, pose, expr)
    h = int(im.height * w / im.width) if im.width > im.height * .9 else int(w * 1.2)
    s = min(w / im.width, (w * 1.45) / im.height)
    out = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    return out.transpose(Image.FLIP_LEFT_RIGHT) if flip else out
