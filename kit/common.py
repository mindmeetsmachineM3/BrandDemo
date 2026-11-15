"""Shared helpers: brand loading, fonts, text fitting, product images, logo chip, footer."""
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"


# ------------------------------------------------------------------ brand
def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


class Brand:
    def __init__(self, path=None):
        self.dir = Path(path).resolve() if path else ROOT / "brand"
        manual, brief = self.dir / "brand.json", self.dir / "prompt.txt"
        if manual.exists():                                          # hand-written profile wins
            self.d = json.loads(manual.read_text(encoding="utf-8"))
        elif brief.exists() and brief.read_text(encoding="utf-8").strip():
            from .profile import build_profile
            import hashlib
            text = brief.read_text(encoding="utf-8")
            sig = hashlib.sha1((text + "|".join(f"{q.name}:{q.stat().st_size}" for q in sorted((self.dir / "assets").rglob("*")) if q.is_file())).encode()).hexdigest()
            cache = ROOT / "output" / "profile_cache.json"
            try:
                c0 = json.loads(cache.read_text(encoding="utf-8"))
            except Exception:
                c0 = {}
            if c0.get("sig") == sig:                                  # same brief and files: do not ask the AI twice
                self.d = c0["profile"]
            else:
                self.d = build_profile(self.dir, text)
                (ROOT / "output").mkdir(exist_ok=True)
                cache.write_text(json.dumps({"sig": sig, "profile": self.d}, ensure_ascii=False), encoding="utf-8")
            (ROOT / "output").mkdir(exist_ok=True)
            (ROOT / "output" / "brand_profile_generated.json").write_text(json.dumps(self.d, ensure_ascii=False, indent=1), encoding="utf-8")
        else:
            raise SystemExit(f"Write the brief in {self.dir}/prompt.txt (or a {self.dir}/brand.json). See README.")
        c = self.d.get("colors", {})
        self.primary = hexrgb(c.get("primary", "#1F6FEB"))
        self.secondary = hexrgb(c.get("secondary", "#FFC83D"))
        self.dark = hexrgb(c.get("dark", "#101828"))
        self.light = hexrgb(c.get("light", "#F7F8FA"))
        self.name = self.d.get("name", "brand")
        self.slug = re.sub(r"[^a-z0-9]+", "_", self.name.lower()).strip("_") or "brand"
        self.handle = self.d.get("handle", "").lstrip("@")
        self.phone = self.d.get("phone", "")
        self.tagline = self.d.get("tagline", "")
        self.lang = self.d.get("language", "english")
        self.post_h = 1350 if self.d.get("post_ratio", "4:5") == "4:5" else 1080
        self.products = self.d.get("products", [])
        self._logo = None
        self._prod = {}

    def problems(self):
        """Things missing in the brand folder, so the demo does not fail halfway."""
        out = []
        if not (self.dir / "assets" / "logo.png").exists():
            out.append("assets/logo.png is missing (the brand name will be written as text instead)")
        if not self.products:
            out.append("brand.json has no products")
        for p in self.products:
            f = self.dir / "assets" / "products" / p.get("image", "")
            if not p.get("image") or not f.exists():
                out.append(f"product '{p.get('id')}': image file not found in assets/products/")
            if not p.get("usps"):
                out.append(f"product '{p.get('id')}': add real benefits under 'usps' (the copy is built from them)")
        for k in ("name", "handle", "tagline", "industry"):
            if not self.d.get(k):
                out.append(f"brand.json: '{k}' is empty")
        if not self.phone:
            out.append("brand.json: no phone, so no call-to-action number will be shown")
        return out

    def logo(self):
        if self._logo is None:
            p = self.dir / "assets" / "logo.png"
            self._logo = Image.open(p).convert("RGBA") if p.exists() else None
        return self._logo

    def product(self, pid):
        if pid not in self._prod:
            item = next((x for x in self.products if x["id"] == pid), None)
            if not item:
                raise SystemExit(f"product id '{pid}' not in brand.json")
            self._prod[pid] = load_product(self.dir / "assets" / "products" / item["image"])
        return self._prod[pid]

    def product_ids(self):
        return [p["id"] for p in self.products]

    def facts_text(self):
        return json.dumps(self.d, ensure_ascii=False)


# ------------------------------------------------------------------ products: transparent PNG preferred, auto cut-out otherwise
def load_product(path):
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"product image missing: {path}")
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im)[..., 3]
    if a.min() < 250:                                   # already has transparency
        bb = im.getbbox()
        return im.crop(bb) if bb else im
    return auto_cutout(im)


def auto_cutout(im, tol=48):
    """Works for pack shots on a plain (white / flat colour) background: flood-fill from the border."""
    rgb = np.asarray(im.convert("RGB")).astype(int)
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg = np.median(border, axis=0)
    dist = np.abs(rgb - bg).sum(2)
    cand = dist < tol
    lab, _ = ndi.label(cand)
    edge_labels = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bgmask = np.isin(lab, list(edge_labels))
    fg = ~bgmask
    fg = ndi.binary_opening(fg, iterations=2)
    fg = ndi.binary_fill_holes(ndi.binary_closing(fg, iterations=2))
    lab2, n = ndi.label(fg)
    if n:
        sizes = ndi.sum(fg, lab2, range(1, n + 1))
        fg = lab2 == (int(np.argmax(sizes)) + 1)
    al = Image.fromarray((fg * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1.0))
    out = im.convert("RGBA")
    out.putalpha(al)
    bb = out.getbbox()
    return out.crop(bb) if bb else out


# ------------------------------------------------------------------ fonts
def _has(text, lo, hi):
    return any(lo <= ord(c) <= hi for c in text)


def font(weight, size, text=""):
    if _has(text, 0x0900, 0x097F):
        p = FONTS / "NotoSansDevanagari-Bold.ttf"
    elif _has(text, 0x0980, 0x09FF):
        p = FONTS / "NotoSansBengali-Bold.ttf"
    else:
        p = FONTS / f"Poppins-{weight}.ttf"
    return ImageFont.truetype(str(p), size)


def wrap(d, text, fnt, max_w):
    lines, cur = [], ""
    for w in str(text).split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fnt) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


def fit(d, text, weight, max_w, max_h, start, min_size=22, lh=1.18):
    """Largest font size (<= start) whose wrapped text fits max_w x max_h. Returns (font, lines, line_height)."""
    size = start
    while True:
        f = font(weight, size, text)
        lines = wrap(d, text, f, max_w)
        h = len(lines) * size * lh
        if (h <= max_h and all(d.textlength(l, font=f) <= max_w * 1.02 for l in lines)) or size <= min_size:
            return f, lines, int(size * lh)
        size -= 2


def draw_lines(d, x, y, lines, f, lh, fill, anchor="la"):
    for ln in lines:
        d.text((x, y), ln, font=f, fill=fill, anchor=anchor)
        y += lh
    return y


def text_fit(d, x, y, text, weight, max_w, max_h, start, fill, min_size=22, lh=1.18, center=False):
    f, lines, h = fit(d, text, weight, max_w, max_h, start, min_size, lh)
    if center:
        for ln in lines:
            d.text((x, y), ln, font=f, fill=fill, anchor="ma")
            y += h
        return y
    return draw_lines(d, x, y, lines, f, h, fill)


# ------------------------------------------------------------------ components
def chip(img, b, x=44, y=40, w=200):
    d = ImageDraw.Draw(img)
    lg = b.logo()
    if lg is None:
        f = font("Bold", 34, b.name)
        tw = int(d.textlength(b.name, font=f))
        d.rounded_rectangle((x, y, x + tw + 44, y + 70), 22, fill=(255, 255, 255))
        d.text((x + 22, y + 35), b.name, font=f, fill=b.dark, anchor="lm")
        return
    h = int(w * lg.height / lg.width)
    d.rounded_rectangle((x, y, x + w + 30, y + h + 30), 22, fill=(255, 255, 255))
    l2 = lg.resize((w, h), Image.LANCZOS)
    img.alpha_composite(l2, (x + 15, y + 15))


def footer(img, b, fill=None, h=78):
    W, H = img.size
    d = ImageDraw.Draw(img)
    d.rectangle((0, H - h, W, H), fill=fill or b.dark)
    d.text((44, H - h // 2), b.tagline or b.name, font=font("Bold", 27, b.tagline), fill=(255, 255, 255), anchor="lm")
    if b.handle:
        d.text((W - 44, H - h // 2), "@" + b.handle, font=font("Bold", 27), fill=b.secondary, anchor="rm")


def pill(img, x, y, text, fill, tc, size=27, padx=26, pady=12):
    d = ImageDraw.Draw(img)
    f = font("Bold", size, text)
    w = d.textlength(text, font=f)
    d.rounded_rectangle((x, y, x + w + 2 * padx, y + size + 2 * pady), (size + 2 * pady) // 2, fill=fill)
    d.text((x + padx, y + pady + size * 0.05), text, font=f, fill=tc)
    return int(x + w + 2 * padx), int(y + size + 2 * pady)


def shadow(img, im, pos, blur=18, off=(10, 22), a=105):
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    m = im.split()[3].point(lambda v: v * a // 255)
    t = Image.new("RGBA", im.size, (0, 0, 0, 255))
    t.putalpha(m)
    sh.paste(t, (pos[0] + off[0], pos[1] + off[1]), t)
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))


def place(img, im, x, y, h=None, w=None, rot=0, drop=True):
    if h is None:
        h = int(im.height * (w / im.width))
    s = h / im.height
    p = im.resize((max(1, int(im.width * s)), max(1, h)), Image.LANCZOS)
    if rot:
        p = p.rotate(rot, resample=Image.BICUBIC, expand=True)
    if drop:
        shadow(img, p, (x, y))
    img.alpha_composite(p, (x, y))
    return p


def products_row(img, b, pids, box, overlap=0.0):
    """Place 1-3 product images side by side inside box=(x0,y0,x1,y1), bottom aligned, scaled to fit."""
    x0, y0, x1, y1 = box
    ims = [b.product(p) for p in pids if p]
    if not ims:
        return
    bw, bh = x1 - x0, y1 - y0
    gap = 10
    # common height so that total width fits
    ratios = [i.width / i.height for i in ims]
    hh = min(bh, (bw - gap * (len(ims) - 1)) / sum(ratios))
    total = sum(r * hh for r in ratios) + gap * (len(ims) - 1)
    x = x0 + (bw - total) / 2
    for i, r in zip(ims, ratios):
        w = r * hh
        place(img, i, int(x), int(y1 - hh), h=int(hh))
        x += w + gap
