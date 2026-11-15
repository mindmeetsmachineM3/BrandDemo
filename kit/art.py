"""Original graphics: patterns, burst/bubble/sparkle shapes, punchy display text with highlighted words,
and procedurally drawn mascots ("blobs") plus a 'product buddy' (the product itself gets eyes, mouth, arms and legs).
Nothing here is copied from any existing character."""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .common import font as pfont, mix, wrap, FONTS, shadow

SS = 3


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def on(c):
    return (22, 22, 30) if lum(c) > 150 else (255, 255, 255)


def A(c, a):
    return tuple(c[:3]) + (int(a),)


# ------------------------------------------------------------------ backgrounds
def gradient(w, h, c1, c2, angle=0.35):
    yy, xx = np.mgrid[0:h, 0:w]
    t = (yy / h * (1 - angle) + xx / w * angle)
    t = t[..., None]
    arr = np.array(c1) * (1 - t) + np.array(c2) * t
    return Image.fromarray(arr.astype("uint8")).convert("RGBA")


def pattern(th, w, h, kind=None, rng=None, strength=.10):
    """Low-contrast decorative layer (RGBA), drawn at 2x and smoothed."""
    kind = kind or th.pattern
    rng = rng or random.Random(th.seed)
    k = 2
    L = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    base = (255, 255, 255) if lum(th.bg) < 150 else (0, 0, 0)
    pc = A(base, 255 * strength * 1.4)
    W, H = w * k, h * k
    if kind == "dots":
        s = 78 * k
        for r_, y in enumerate(range(0, H + s, s)):
            for x in range(-s, W + s, s):
                xx = x + (s // 2 if r_ % 2 else 0)
                d.ellipse((xx - 13 * k, y - 13 * k, xx + 13 * k, y + 13 * k), fill=pc)
    elif kind == "stripes":
        s = 120 * k
        for x in range(-H, W + H, s):
            d.polygon([(x, 0), (x + s // 2, 0), (x + s // 2 + H * .6, H), (x + H * .6, H)], fill=pc)
    elif kind == "sunburst":
        cx, cy, n = W * rng.uniform(.3, .7), H * rng.uniform(.35, .6), 28
        R = (W + H)
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + .5) / n
            d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)), (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=pc)
    elif kind == "blobs":
        for _ in range(8):
            r = rng.randint(90, 260) * k
            x, y = rng.randint(0, W), rng.randint(0, H)
            d.ellipse((x - r, y - r * rng.uniform(.7, 1.1), x + r, y + r), fill=A(base, 255 * strength * rng.uniform(.6, 1.6)))
    elif kind == "grid":
        s = 90 * k
        for x in range(0, W, s):
            d.line((x, 0, x, H), fill=pc, width=3 * k)
        for y in range(0, H, s):
            d.line((0, y, W, y), fill=pc, width=3 * k)
    elif kind == "halftone":
        s = 54 * k
        for y in range(0, H + s, s):
            for x in range(0, W + s, s):
                t = (y / H) * .85 + .1
                r = s * .5 * t
                d.ellipse((x - r, y - r, x + r, y + r), fill=pc)
    elif kind == "waves":
        s = 110 * k
        for y in range(-s, H + s, s):
            pts = [(x, y + math.sin(x / (90 * k) + y / 200) * 28 * k) for x in range(0, W + 20, 20)]
            d.line(pts, fill=pc, width=22 * k)
    elif kind == "confetti":
        cols = [th.accent, th.accent2, th.card, mix(th.bg2, (255, 255, 255), .4)]
        for _ in range(70):
            x, y = rng.randint(0, W), rng.randint(0, H)
            c = A(rng.choice(cols), 150)
            s = rng.randint(10, 26) * k
            sh = rng.choice("rct")
            a = rng.uniform(0, 6.28)
            if sh == "c":
                d.ellipse((x - s / 2, y - s / 2, x + s / 2, y + s / 2), fill=c)
            else:
                n = 4 if sh == "r" else 3
                pts = [(x + s * (1 if sh == "t" else .5) * math.cos(a + 6.28 * i / n + (.78 if n == 4 else 0)),
                        y + s * (1 if sh == "t" else .5) * math.sin(a + 6.28 * i / n + (.78 if n == 4 else 0))) for i in range(n)]
                d.polygon(pts, fill=c)
    elif kind == "zigzag":
        s = 100 * k
        for y in range(0, H + s, s):
            pts = [(x, y + (24 * k if (i % 2) else 0)) for i, x in enumerate(range(0, W + 60 * k, 60 * k))]
            d.line(pts, fill=pc, width=10 * k, joint="curve")
    elif kind == "checker":
        s = 100 * k
        for r_, y in enumerate(range(0, H, s)):
            for c_, x in enumerate(range(0, W, s)):
                if (r_ + c_) % 2:
                    d.rectangle((x, y, x + s, y + s), fill=pc)
    return L.resize((w, h), Image.LANCZOS)


def background(th, w, h, kind=None, rng=None):
    img = gradient(w, h, th.bg, th.bg2, .35 + (th.seed % 5) * .1)
    img.alpha_composite(pattern(th, w, h, kind, rng))
    return img


# ------------------------------------------------------------------ small shapes (supersampled)
def _ss(img, box, fn):
    """draw with fn(draw, s) on a transparent layer of the box area at SS x resolution, composite smoothly"""
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    L = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    fn(ImageDraw.Draw(L), lambda v: v * SS, (x0, y0))
    img.alpha_composite(L.resize((w, h), Image.LANCZOS), (x0, y0))


def burst(img, cx, cy, r, fill, outline, n=14, depth=.16, rot=0, ow=6):
    def f(d, s, o):
        def poly(rr):
            pts = []
            for i in range(n * 2):
                a = rot + math.pi * i / n
                q = rr * (1 if i % 2 == 0 else 1 - depth)
                pts.append((s(cx - o[0] + q * math.cos(a)), s(cy - o[1] + q * math.sin(a))))
            return pts
        d.polygon(poly(r + ow), fill=outline)
        d.polygon(poly(r), fill=fill)
    m = r + 14
    _ss(img, (cx - m, cy - m, cx + m, cy + m), f)


def sparkle(img, cx, cy, r, fill):
    def f(d, s, o):
        pts = []
        for i in range(8):
            a = math.pi * i / 4 - math.pi / 2
            q = r if i % 2 == 0 else r * .28
            pts.append((s(cx - o[0] + q * math.cos(a)), s(cy - o[1] + q * math.sin(a))))
        d.polygon(pts, fill=fill)
    _ss(img, (cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4), f)


def squiggle(img, x0, y, x1, color, amp=10, w=8, waves=6):
    def f(d, s, o):
        pts = [(s(x - o[0]), s(y - o[1] + math.sin((x - x0) / (x1 - x0) * waves * 2 * math.pi) * amp)) for x in range(int(x0), int(x1), 3)]
        d.line(pts, fill=color, width=s(w), joint="curve")
        for p in (pts[0], pts[-1]):
            d.ellipse((p[0] - s(w) / 2, p[1] - s(w) / 2, p[0] + s(w) / 2, p[1] + s(w) / 2), fill=color)
    _ss(img, (x0 - 10, y - amp - w - 6, x1 + 10, y + amp + w + 6), f)


def rrect(img, box, radius, fill, outline=None, ow=0, shadow=0, rot=0):
    """rounded rectangle, antialiased, optional hard offset shadow and rotation"""
    x0, y0, x1, y1 = box
    pad = 40 + shadow
    w, h = int(x1 - x0 + 2 * pad), int(y1 - y0 + 2 * pad)
    L = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    b = (pad * SS, pad * SS, (pad + x1 - x0) * SS, (pad + y1 - y0) * SS)
    if shadow:
        d.rounded_rectangle((b[0] + shadow * SS, b[1] + shadow * SS, b[2] + shadow * SS, b[3] + shadow * SS), radius * SS, fill=(15, 12, 30, 255))
    d.rounded_rectangle(b, radius * SS, fill=fill, outline=outline, width=ow * SS)
    L = L.resize((w, h), Image.LANCZOS)
    if rot:
        L = L.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(L, (int((x0 + x1) / 2 - L.width / 2), int((y0 + y1) / 2 - L.height / 2)))


def bubble(img, th, text, cx, cy, maxw, tail=(0, 0), start=44, maxh=260, fill=None, ink=None, rot=0):
    """Speech bubble centred on (cx, cy) whose tail points to `tail`. Returns bubble bottom y."""
    fill = fill or (255, 255, 255)
    ink = ink or (22, 22, 30)
    tmp = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    size = start
    while True:
        f = pfont("Bold", size, text)
        lines = wrap(tmp, text, f, maxw - 60)
        h = len(lines) * size * 1.2
        if (h <= maxh and all(tmp.textlength(l, font=f) <= maxw - 50 for l in lines)) or size <= 24:
            break
        size -= 2
    tw = max(tmp.textlength(l, font=f) for l in lines)
    bw, bh = tw + 64, h + 44
    x0, y0, x1, y1 = cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2
    m = 40
    ox, oy = min(x0, tail[0]) - m, min(y0, tail[1]) - m
    W_, H_ = int(max(x1, tail[0]) + m - ox), int(max(y1, tail[1]) + m - oy)
    L = Image.new("RGBA", (W_ * SS, H_ * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    s = lambda v: v * SS
    tx, ty = tail
    # tail: triangle from the bubble edge towards the target
    bx = min(max(tx, x0 + 50), x1 - 50)
    by = y1 if ty > cy else y0
    tri = [(bx - 26, by), (bx + 26, by), (tx, ty)]
    for off, col in ((0, ink), (-1, fill)):
        pass
    d.rounded_rectangle((s(x0 - ox - 6), s(y0 - oy - 6), s(x1 - ox + 6), s(y1 - oy + 6)), s(34), fill=ink)
    d.polygon([(s(a - ox + (0 if i == 2 else 0)), s(b_ - oy)) for i, (a, b_) in enumerate(tri)], fill=ink)
    d.rounded_rectangle((s(x0 - ox), s(y0 - oy), s(x1 - ox), s(y1 - oy)), s(30), fill=fill)
    tri2 = [(bx - 20, by + (-4 if ty > cy else 4)), (bx + 20, by + (-4 if ty > cy else 4)), (tx + (bx - tx) * .06, ty + (cy - ty) * .06)]
    d.polygon([(s(a - ox), s(b_ - oy)) for a, b_ in tri2], fill=fill)
    L = L.resize((W_, H_), Image.LANCZOS)
    if rot:
        L = L.rotate(rot, resample=Image.BICUBIC, expand=True, center=((cx - ox), (cy - oy)))
    img.alpha_composite(L, (int(ox), int(oy)))
    d2 = ImageDraw.Draw(img)
    y = cy - h / 2 + size * .08 + 22
    # text is drawn unrotated for crispness when rot is small
    for ln in lines:
        d2.text((cx, y), ln, font=f, fill=ink, anchor="ma")
        y += size * 1.2
    return int(y1)


# ------------------------------------------------------------------ display text
def dfont(th, size, text):
    if any(ord(c) > 0x2000 and c not in "’‘“”–—…" for c in text):
        return pfont("Bold", size, text)               # Indic scripts, rupee sign: fall back to Poppins / Noto
    return ImageFont.truetype(str(th.font_path()), size)


def _clean(w):
    return "".join(ch for ch in w.lower() if ch.isalnum())


def draw_word(img, x, y, word, f, fill, th, effect, size):
    d = ImageDraw.Draw(img)
    if effect == "shadow3d":
        n = max(3, size // 15)
        sc = th.dark if abs(lum(fill) - lum(th.dark)) > 90 else ((255, 255, 255) if lum(fill) < 130 else th.dark)
        for k in range(n, 0, -1):
            d.text((x + k, y + k), word, font=f, fill=sc)
        d.text((x, y), word, font=f, fill=fill)
    elif effect == "outline":
        d.text((x + size // 16, y + size // 16), word, font=f, fill=th.dark, stroke_width=max(2, size // 26), stroke_fill=th.dark)
        d.text((x, y), word, font=f, fill=fill, stroke_width=max(2, size // 30), stroke_fill=th.dark)
    elif effect == "sticker":
        sw = max(3, size // 20)
        d.text((x + size // 14, y + size // 14), word, font=f, fill=th.dark, stroke_width=sw, stroke_fill=th.dark)
        d.text((x, y), word, font=f, fill=fill, stroke_width=sw, stroke_fill=(255, 255, 255) if lum(th.bg) < 170 else th.card)
    else:
        d.text((x, y), word, font=f, fill=fill)


def rich(img, th, text, hl, box, start=120, min_size=36, align="center", fill=None, hlfill=None, effect=None, lh=1.1, rot=0, upper=None):
    """Display headline in the theme font. Words that appear in `hl` get the highlight colour.
    Fits the box by shrinking. Returns the bottom y."""
    text = (text or "").strip()
    if not text:
        return box[1]
    x0, y0, x1, y1 = box
    effect = effect or th.effect
    fill = fill or th.ink
    hlfill = hlfill or th.accent
    up = th.upper if upper is None else upper
    if up and not any(ord(c) > 0x2000 for c in text):
        text = text.upper()
    hlw = {_clean(w) for w in (hl or "").split()} - {""}
    tmp = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    size = start
    while True:
        f = dfont(th, size, text)
        sp = tmp.textlength(" ", font=f) * 1.1
        lines, cur, cw = [], [], 0
        for w in text.split():
            ww = tmp.textlength(w, font=f)
            if cur and cw + sp + ww > (x1 - x0) - size * .15:
                lines.append(cur)
                cur, cw = [], 0
            cw += (sp if cur else 0) + ww
            cur.append(w)
        if cur:
            lines.append(cur)
        widths = [sum(tmp.textlength(w, font=f) for w in ln) + sp * (len(ln) - 1) for ln in lines]
        hh = len(lines) * size * lh
        if (hh <= (y1 - y0) and max(widths) <= (x1 - x0)) or size <= min_size:
            break
        size -= 3
    pad = int(size * .5)
    Lw, Lh = int(x1 - x0 + 2 * pad), int(hh + 2 * pad + size * .3)
    L = Image.new("RGBA", (Lw, Lh), (0, 0, 0, 0))
    y = pad
    for ln, wd in zip(lines, widths):
        x = pad + ((x1 - x0) - wd) / 2 if align == "center" else pad
        for w in ln:
            col = hlfill if _clean(w) in hlw else fill
            draw_word(L, x, y, w, f, col, th, effect, size)
            x += tmp.textlength(w, font=f) + sp
        y += size * lh
    if rot:
        L = L.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(L, (int((x0 + x1) / 2 - L.width / 2) if align == "center" else int(x0 - pad), int(y0 - pad + (0 if not rot else -(L.height - Lh) / 2))))
    return int(y0 + hh)


# ------------------------------------------------------------------ mascots
def _body(d, S, kind, expand, fill):
    e = expand
    if kind == "round":
        d.ellipse(S(16 - e, 24 - e, 84 + e, 94 + e), fill=fill)
    elif kind == "squircle":
        d.rounded_rectangle(S(20 - e, 18 - e, 80 + e, 94 + e), int(S(26)[0]), fill=fill)
    elif kind == "drop":
        d.ellipse(S(18 - e, 36 - e, 82 + e, 96 + e), fill=fill)
        d.polygon(S(50, 4 - e * 1.4, 26 - e * .6, 56, 74 + e * .6, 56), fill=fill)
    else:  # bean
        d.ellipse(S(22 - e, 12 - e, 78 + e, 96 + e), fill=fill)


TOPY = {"bean": 12, "round": 24, "squircle": 18, "drop": 6}
ARMS = {"wave": ((12, 78, 8, 94), (86, 28, 92, 14)), "cheer": ((12, 32, 6, 16), (88, 32, 94, 16)),
        "point": ((14, 70, 10, 82), (96, 50, 112, 46)), "hold": ((30, 86, 44, 88), (70, 86, 56, 88)),
        "shrug": ((10, 56, 2, 46), (90, 56, 98, 46)), "stand": ((14, 74, 10, 90), (86, 74, 90, 90))}


def _line(d, S, pts, col, w):
    P = [S(*p) if False else (S(p[0])[0], S(p[1])[0]) for p in pts]
    d.line(P, fill=col, width=int(S(w)[0]), joint="curve")
    r = S(w)[0] / 2
    for p in (P[0], P[-1]):
        d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=col)


def _arms(d, S, pose, col, dark, sx=None):
    for (x1, y1, x2, y2), sh in zip(ARMS.get(pose, ARMS["stand"]), ((26, 60), (74, 60))):
        mid = ((sh[0] + x1) / 2, (sh[1] + y1) / 2 + 4) if pose in ("shrug", "hold") else ((sh[0] + x1) / 2, (sh[1] + y1) / 2)
        if pose == "hold":
            pts = [sh, (x1, y1)]
        else:
            pts = [sh, (x1, y1), (x2, y2)] if pose in ("wave", "cheer", "point", "shrug") else [sh, (x1, y1), (x2, y2)]
        if pose == "wave" or pose == "cheer" or pose == "shrug" or pose == "point":
            pts = [sh, (x1, y1)] if False else [sh, (x1, y1), (x2, y2)]
        _line(d, S, pts, dark, 11)
        _line(d, S, pts, col, 6.4)
        hx, hy = pts[-1]
        r = S(5.6)[0]
        cx, cy = S(hx)[0], S(hy)[0]
        d.ellipse((cx - r - S(1.6)[0], cy - r - S(1.6)[0], cx + r + S(1.6)[0], cy + r + S(1.6)[0]), fill=dark)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)


def _eyes(d, S, cx, cy, gap, r, expr, dark, look=(0, 0), wink=False):
    for i, sgn in enumerate((-1, 1)):
        x, y = cx + sgn * gap, cy
        if expr == "wink" and i == 1:
            d.arc(S(x - r, y - r * .5, x + r, y + r * 1.1), 200, 340, fill=dark, width=int(S(r * .38)[0]))
            continue
        rr = r * (1.25 if expr == "wow" else 1)
        d.ellipse(S(x - rr - 1.2, y - rr - 1.2, x + rr + 1.2, y + rr + 1.2), fill=dark)
        d.ellipse(S(x - rr, y - rr, x + rr, y + rr), fill=(255, 255, 255))
        pr = rr * (.34 if expr == "wow" else .5)
        px, py = x + look[0] * rr * .35, y + look[1] * rr * .35
        d.ellipse(S(px - pr, py - pr, px + pr, py + pr), fill=dark)
        d.ellipse(S(px - pr * .38 + pr * .3, py - pr * .8, px + pr * .3, py - pr * .1), fill=(255, 255, 255))
        if expr == "sad":
            d.line([S(x - rr * 1.1, y - rr * (1.15 if sgn < 0 else 1.7)), S(x + rr * 1.1, y - rr * (1.7 if sgn < 0 else 1.15))], fill=dark, width=int(S(r * .34)[0]))
        elif expr == "smirk" and i == 1:
            d.line([S(x - rr, y - rr * 1.5), S(x + rr, y - rr * 1.9)], fill=dark, width=int(S(r * .34)[0]))


def _mouth(d, S, cx, cy, w, expr, dark, halo=None):
    wd = int(S(w * .16)[0])
    def go(col, extra):
        e = extra
        if expr in ("grin", "wink"):
            d.chord(S(cx - w / 2 - e, cy - w * .18 - e, cx + w / 2 + e, cy + w * .5 + e), 0, 180, fill=col)
        elif expr == "wow":
            d.ellipse(S(cx - w * .2 - e, cy - w * .08 - e, cx + w * .2 + e, cy + w * .42 + e), fill=col)
        elif expr == "sad":
            d.arc(S(cx - w / 2 - e, cy - w * .05 - e, cx + w / 2 + e, cy + w * .5 + e), 205, 335, fill=col, width=wd + int(S(e * 2)[0]))
        else:   # smirk
            d.arc(S(cx - w / 2 - e, cy - w * .35 - e, cx + w / 2 + e, cy + w * .3 + e), 25, 150, fill=col, width=wd + int(S(e * 2)[0]))
    if halo:
        go(halo, w * .06)
    go(dark, 0)
    if expr in ("grin", "wink"):
        d.chord(S(cx - w * .26, cy + w * .2, cx + w * .26, cy + w * .5), 0, 180, fill=(255, 112, 140))
    if expr == "sad":
        d.ellipse(S(cx + w * .8, cy - w * .55, cx + w * 1.0, cy - w * .2), fill=(96, 190, 255))


def _acc(d, S, kind, ty, th, dark):
    a1, a2 = th.accent, th.accent2
    if kind == "cap":
        d.pieslice(S(30, ty - 12, 70, ty + 26), 180, 360, fill=a2)
        d.rounded_rectangle(S(46, ty + 8, 84, ty + 15), int(S(3.5)[0]), fill=a2)
        d.arc(S(30, ty - 12, 70, ty + 26), 180, 360, fill=dark, width=int(S(2)[0]))
    elif kind == "hardhat":
        d.pieslice(S(28, ty - 14, 72, ty + 28), 180, 360, fill=(255, 205, 40))
        d.rounded_rectangle(S(24, ty + 8, 76, ty + 15), int(S(3.5)[0]), fill=(255, 205, 40))
        d.rectangle(S(46, ty - 12, 54, ty + 8), fill=(235, 170, 10))
        d.arc(S(28, ty - 14, 72, ty + 28), 180, 360, fill=dark, width=int(S(2)[0]))
    elif kind == "crown":
        d.polygon(S(32, ty + 12, 32, ty - 8, 41, ty + 2, 50, ty - 12, 59, ty + 2, 68, ty - 8, 68, ty + 12), fill=(255, 200, 40), outline=dark)
        d.ellipse(S(47.5, ty - 6, 52.5, ty - 1), fill=(235, 60, 90))
    elif kind == "headband":
        d.rounded_rectangle(S(24, ty + 8, 76, ty + 15), int(S(4)[0]), fill=a2, outline=dark, width=int(S(1.4)[0]))
        d.polygon(S(76, ty + 11, 90, ty + 5, 88, ty + 19), fill=a2)
    elif kind == "antenna":
        d.line([S(50, ty + 2)[0:2], S(50, ty - 16)[0:2]] if False else [S(50, ty + 2), S(50, ty - 16)], fill=dark, width=int(S(2.6)[0]))
        d.ellipse(S(44, ty - 24, 56, ty - 12), fill=a1, outline=dark, width=int(S(1.6)[0]))
    elif kind == "sprout":
        d.line([S(50, ty + 2), S(50, ty - 10)], fill=dark, width=int(S(3)[0]))
        d.ellipse(S(50, ty - 22, 68, ty - 8), fill=(70, 190, 90), outline=dark, width=int(S(1.4)[0]))
        d.ellipse(S(32, ty - 20, 50, ty - 7), fill=(100, 210, 110), outline=dark, width=int(S(1.4)[0]))
    elif kind == "party":
        d.polygon(S(36, ty + 16, 50, ty - 22, 64, ty + 16), fill=a1, outline=dark)
        d.line([S(41, ty + 2), S(59, ty + 2)], fill=a2, width=int(S(3)[0]))
        d.line([S(44, ty - 8), S(56, ty - 8)], fill=a2, width=int(S(3)[0]))
        d.ellipse(S(45, ty - 28, 55, ty - 18), fill=a2)
    elif kind == "bow":
        d.polygon(S(58, ty + 8, 74, ty - 2, 74, ty + 18), fill=a1, outline=dark)
        d.polygon(S(58, ty + 8, 42, ty - 2, 42, ty + 18), fill=a1, outline=dark)
        d.ellipse(S(54, ty + 4, 62, ty + 12), fill=a2, outline=dark)
    elif kind == "glasses":
        pass


def _glasses(d, S, cx, cy, gap, r, dark):
    for sgn in (-1, 1):
        x = cx + sgn * gap
        d.ellipse(S(x - r * 1.5, cy - r * 1.5, x + r * 1.5, cy + r * 1.5), outline=dark, width=int(S(1.8)[0]))
    d.line([S(cx - gap + r * 1.5, cy), S(cx + gap - r * 1.5, cy)], fill=dark, width=int(S(1.8)[0]))


def blob(th, w=420, pose="wave", expr="grin", acc=None, body=None, color=None, look=(0, 0), flip=False):
    """Original blob character as an RGBA sprite, w px wide."""
    acc = th.acc if acc is None else acc
    body = body or th.body
    col = color or th.char_col
    dark = th.dark if lum(th.dark) < 90 else (20, 16, 36)
    k = w * SS / 100
    h = int(w * 1.2)
    L = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)

    def S(*v):
        return tuple(int(x * k) for x in v)
    # legs
    for sx in (-1, 1):
        _line(d, S, [(50 + sx * 12, 90), (50 + sx * 13, 108)], dark, 10.5)
        _line(d, S, [(50 + sx * 12, 90), (50 + sx * 13, 108)], col, 6)
        d.ellipse(S(50 + sx * 13 - 8 + sx * 2, 104, 50 + sx * 13 + 8 + sx * 2, 113), fill=dark)
    if pose != 'hold':
        _arms(d, S, pose, col, dark)
    _body(d, S, body, 2.6, dark)
    _body(d, S, body, 0, col)
    if pose == 'hold':
        _arms(d, S, pose, col, dark)
    # belly shine + cheeks
    hi = mix(col, (255, 255, 255), .45)
    d.ellipse(S(30, 28 + TOPY[body] * .3, 38, 46 + TOPY[body] * .3), fill=A(hi, 150)) if body != "drop" else None
    _eyes(d, S, 50, 50, 10.5, 6.6, expr, dark, look)
    for sx in (-1, 1):
        d.ellipse(S(50 + sx * 21 - 5, 61, 50 + sx * 21 + 5, 67), fill=(255, 130, 150, 150))
    _mouth(d, S, 50, 64, 15, expr, dark)
    if acc == "glasses":
        _glasses(d, S, 50, 50, 10.5, 6.6, dark)
    else:
        _acc(d, S, acc, TOPY[body], th, dark)
    out = L.resize((w, h), Image.LANCZOS)
    return out.transpose(Image.FLIP_LEFT_RIGHT) if flip else out


def buddy(th, prod, h=560, pose="wave", expr="grin", face_y=.27, feet=True):
    """The product itself comes alive: eyes, mouth, arms and legs drawn over the cut-out."""
    pw = int(prod.width * h / prod.height)
    pad_x, pad_b, pad_t = int(max(pw * .42, h * .28)), int(h * .22 if feet else 0), int(h * .12)
    W_, H_ = pw + 2 * pad_x, h + pad_b + pad_t
    k = SS
    L = Image.new("RGBA", (W_ * k, H_ * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    dark = th.dark if lum(th.dark) < 90 else (20, 16, 36)
    u = h / 100.0                                    # 1 unit = 1% of product height
    col = th.char_col
    # unit space mapped to the sprite
    ox, oy = pad_x, pad_t

    def S(*v):
        return tuple(int((ox + a * u) * k) if i % 2 == 0 else int((oy + a * u) * k) for i, a in enumerate(v))

    def Sw(x_pct, y_pct):                           # x as % of product width, y % of height
        return (ox + x_pct / 100 * pw) * k, (oy + y_pct / 100 * h) * k
    if feet:
        for sx in (.3, .7):
            x = pw * sx
            d.line([((ox + x) * k, (oy + h - 4) * k), ((ox + x) * k, (oy + h + h * .13) * k)], fill=dark, width=int(h * .06 * k))
            d.line([((ox + x) * k, (oy + h - 4) * k), ((ox + x) * k, (oy + h + h * .13) * k)], fill=col, width=int(h * .036 * k))
            fx = (ox + x) * k
            fy = (oy + h + h * .14) * k
            d.ellipse((fx - h * .075 * k + (-1 if sx < .5 else 1) * h * .02 * k, fy - h * .03 * k, fx + h * .075 * k + (-1 if sx < .5 else 1) * h * .02 * k, fy + h * .03 * k), fill=dark)
    # arms from the sides of the pack
    arm = ARMS.get(pose, ARMS["stand"])
    lw = h * .06 * k
    for sgn, (x1, y1, x2, y2) in zip((-1, 1), arm):
        sx = (ox + (pw * .04 if sgn < 0 else pw * .96)) * k
        sy = (oy + h * .52) * k
        ex = sx + sgn * ((abs(x1 - 12) + 6) / 100 * h * 1.0) * k * (1 if pose != "hold" else .1)
        ey = (oy + h * (y1 / 100 * 1.05 - .05 + .12)) * k
        if pose == "hold":
            ex, ey = sx + sgn * -pw * .15 * k, (oy + h * .78) * k
        pts = [(sx, sy), (ex, ey)]
        if pose in ("wave", "cheer"):
            if (pose == "cheer") or sgn > 0:
                pts = [(sx, sy), (sx + sgn * h * .2 * k, sy - h * .08 * k), (sx + sgn * h * .22 * k, sy - h * .3 * k)]
            else:
                pts = [(sx, sy), (sx - h * .16 * k, sy + h * .12 * k)]
        elif pose == "point":
            pts = [(sx, sy), (sx + sgn * h * .12 * k, sy + h * .1 * k)] if sgn < 0 else [(sx, sy), (sx + h * .3 * k, sy - h * .03 * k)]
        elif pose == "shrug":
            pts = [(sx, sy), (sx + sgn * h * .18 * k, sy + h * .02 * k), (sx + sgn * h * .24 * k, sy - h * .12 * k)]
        for c, wd in ((dark, lw * 1.0), (col, lw * .6)):
            d.line(pts, fill=c, width=int(wd), joint="curve")
            for p in (pts[0], pts[-1]):
                d.ellipse((p[0] - wd / 2, p[1] - wd / 2, p[0] + wd / 2, p[1] + wd / 2), fill=c)
        hx, hy = pts[-1]
        r = h * .05 * k
        d.ellipse((hx - r * 1.25, hy - r * 1.25, hx + r * 1.25, hy + r * 1.25), fill=dark)
        d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=col)
    L = L.resize((W_, H_), Image.LANCZOS)
    pr = prod.resize((pw, h), Image.LANCZOS)
    # soft white outline so the product reads as a sticker
    L.alpha_composite(pr, (pad_x, pad_t))
    # face on top (own supersampled layer)
    F = Image.new("RGBA", (W_ * k, H_ * k), (0, 0, 0, 0))
    fd = ImageDraw.Draw(F)
    cx, cy = (ox + pw / 2) * k, (oy + h * face_y) * k
    er = max(h * .045, min(pw * .1, h * .085)) * k
    gap = er * 1.9
    ink = (20, 16, 36)

    def S2(*v):
        out = []
        for i, a in enumerate(v):
            out.append(int(a))
        return tuple(out)
    # reuse the mascot face helpers with an identity scale
    ident = lambda *v: tuple(v) if len(v) > 1 else (v[0],)
    _eyes(fd, ident, cx, cy, gap, er, expr, ink)
    _mouth(fd, ident, cx, cy + er * 2.0, er * 3.0, expr, ink, halo=(255, 255, 255))
    for sgn in (-1, 1):
        fd.ellipse((cx + sgn * gap * 1.7 - er * .7, cy + er * 1.5, cx + sgn * gap * 1.7 + er * .7, cy + er * 2.2), fill=(255, 120, 150, 150))
    F = F.resize((W_, H_), Image.LANCZOS)
    L.alpha_composite(F)
    return L


def shadow_under(img, cx, y, w, a=70):
    L = Image.new("RGBA", (int(w * 1.4), int(w * .3)), (0, 0, 0, 0))
    ImageDraw.Draw(L).ellipse((int(w * .2), int(w * .08), int(w * 1.2), int(w * .24)), fill=(0, 0, 0, a))
    L = L.filter(ImageFilter.GaussianBlur(10))
    img.alpha_composite(L, (int(cx - L.width / 2), int(y - L.height / 2)))


# ------------------------------------------------------------------ realistic-style people (original, procedurally drawn, no real person)
SKINS = [(247, 214, 184), (234, 190, 150), (214, 160, 113), (190, 130, 88), (160, 104, 66), (126, 80, 50)]
HAIRS = [(24, 20, 20), (42, 30, 26), (60, 42, 30), (90, 90, 96)]
ROLES = [  # name, outfit, accessory, hair styles allowed
    ("painter", "overall", "hardhat", ["short", "beard", "bald"]),
    ("homeowner", "shirt", "none", ["short", "side", "beard"]),
    ("designer", "shirt", "glasses", ["bun", "long", "side", "short"]),
    ("shopkeeper", "apron", "none", ["short", "beard", "side"]),
    ("homemaker", "dress", "none", ["bun", "long", "ponytail"]),
    ("student", "shirt", "cap", ["short", "ponytail", "side"]),
    ("engineer", "shirt", "glasses", ["short", "side", "long"]),
]
ARMSP = {"wave": ((20, 66, 18, 84), (80, 44, 86, 26)), "cheer": ((18, 40, 12, 22), (82, 40, 88, 22)),
         "point": ((20, 66, 22, 84), (88, 52, 104, 50)), "hold": ((28, 70, 42, 80), (72, 70, 58, 80)),
         "shrug": ((14, 60, 8, 46), (86, 60, 92, 46)), "stand": ((22, 66, 22, 84), (78, 66, 78, 84))}


TRADE = ("paint", "hardware", "build", "construct", "tool", "cement", "tile", "plumb", "electric", "furnitur", "home improvement")


def roles_for(industry=""):
    trade = any(t in (industry or "").lower() for t in TRADE)
    pool = [r for r in ROLES if trade or r[0] not in ("painter", "engineer")]
    return pool


def make_person(rng, top_choices, bg, role=None):
    role = role or rng.choice(ROLES)
    top = rng.choice([c for c in top_choices if abs(lum(c) - lum(bg)) > 45] or top_choices)
    return dict(role=role[0], outfit=role[1], acc=role[2], hair=rng.choice(HAIRS), style=rng.choice(role[3]), skin=rng.choice(SKINS),
                top=top, pants=rng.choice([(40, 52, 84), (52, 52, 60), (110, 84, 60), (30, 60, 70)]))


def person(th, w=420, pose="wave", expr="grin", flip=False, look=(0, 0)):
    P = th.person
    k = w * SS / 100
    h = int(w * 1.2)
    L = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    dark = (28, 22, 36)
    skin, skin2 = P["skin"], mix(P["skin"], (90, 40, 20), .25)
    hair, top, pants = P["hair"], P["top"], P["pants"]
    ow = max(2, int(1.5 * k))

    def S(*v):
        return tuple(int(x * k) for x in v)
    dress = P["outfit"] == "dress"
    # legs / skirt
    if dress:
        d.polygon(S(33, 62, 67, 62, 74, 100, 26, 100), fill=mix(top, (0, 0, 0), .1), outline=dark, width=ow)
        for sx in (43, 57):
            d.rounded_rectangle(S(sx - 4, 99, sx + 4, 112), int(2 * k), fill=skin, outline=dark, width=ow)
    else:
        for sx in (43, 57):
            d.rounded_rectangle(S(sx - 6, 78, sx + 6, 111), int(4 * k), fill=pants, outline=dark, width=ow)
    for sx, dx in ((43, -2), (57, 2)):
        d.ellipse(S(sx - 8 + dx, 108, sx + 8 + dx, 117), fill=dark)
    # back hair for long styles
    if P["style"] == "long":
        d.rounded_rectangle(S(33, 12, 67, 60), int(12 * k), fill=hair, outline=dark, width=ow)
    # arms (behind torso unless hold)
    def arms():
        for (ex, ey, hx, hy), sh in zip(ARMSP.get(pose, ARMSP["stand"]), ((32, 52), (68, 52))):
            _line(d, S, [sh, (ex, ey)], dark, 10.5)
            _line(d, S, [sh, (ex, ey)], top, 7.4)
            _line(d, S, [(ex, ey), (hx, hy)], dark, 8.6)
            _line(d, S, [(ex, ey), (hx, hy)], skin, 5.6)
            r = S(4.6)[0]
            cx, cy = S(hx)[0], S(hy)[0]
            d.ellipse((cx - r - ow, cy - r - ow, cx + r + ow, cy + r + ow), fill=dark)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=skin)
    if pose != "hold":
        arms()
    # torso
    if dress:
        d.rounded_rectangle(S(30, 44, 70, 72), int(12 * k), fill=top, outline=dark, width=ow)
    else:
        d.rounded_rectangle(S(29, 44, 71, 84), int(13 * k), fill=top, outline=dark, width=ow)
    if P["outfit"] == "apron":
        d.rounded_rectangle(S(36, 58, 64, 86), int(6 * k), fill=mix(top, (255, 255, 255), .75), outline=dark, width=ow)
        d.line([S(36, 58), S(36, 48)], fill=dark, width=ow)
        d.line([S(64, 58), S(64, 48)], fill=dark, width=ow)
    if P["outfit"] == "overall":
        d.rounded_rectangle(S(35, 60, 65, 86), int(5 * k), fill=pants, outline=dark, width=ow)
        d.rectangle(S(36, 46, 40, 62), fill=pants)
        d.rectangle(S(60, 46, 64, 62), fill=pants)
    if pose == "hold":
        arms()
    # neck + head
    d.rounded_rectangle(S(45, 36, 55, 48), int(3 * k), fill=skin2, outline=dark, width=ow)
    d.ellipse(S(33, 22, 38, 33), fill=skin, outline=dark, width=ow)
    d.ellipse(S(62, 22, 67, 33), fill=skin, outline=dark, width=ow)
    d.ellipse(S(35, 9, 65, 44), fill=skin, outline=dark, width=ow)
    # hair front
    st = P["style"]
    if st in ("short", "side", "beard", "bun", "ponytail", "long"):
        d.chord(S(34, 6, 66, 38), 180, 360, fill=hair, outline=dark, width=ow)
        if st == "side":
            d.polygon(S(34, 22, 36, 11, 64, 14, 62, 22, 52, 15), fill=hair)
        if st == "bun":
            d.ellipse(S(43, -2, 57, 11), fill=hair, outline=dark, width=ow)
        if st == "ponytail":
            d.polygon(S(62, 14, 78, 22, 72, 40, 66, 24), fill=hair, outline=dark)
        if st == "long":
            d.rectangle(S(34, 18, 38, 40), fill=hair)
            d.rectangle(S(62, 18, 66, 40), fill=hair)
    elif st == "bald":
        d.arc(S(35, 9, 65, 44), 200, 340, fill=mix(skin, (255, 255, 255), .4), width=int(2 * k))
    # face
    ex, ey, eg = 50, 27, 5.8
    for i, sgn in enumerate((-1, 1)):
        x = ex + sgn * eg
        if expr == "wink" and i == 1:
            d.arc(S(x - 2.8, ey - 1.5, x + 2.8, ey + 2), 200, 340, fill=dark, width=int(1.2 * k))
            continue
        rr = 3.1 if expr != "wow" else 3.7
        d.ellipse(S(x - rr, ey - rr * .85, x + rr, ey + rr * .85), fill=(255, 255, 255), outline=dark, width=max(1, int(.6 * k)))
        ir = 1.9 if expr != "wow" else 1.5
        d.ellipse(S(x - ir + look[0], ey - ir + look[1], x + ir + look[0], ey + ir + look[1]), fill=(46, 30, 22))
        d.ellipse(S(x - .5 + look[0], ey - 1.2 + look[1], x + .7 + look[0], ey - .1 + look[1]), fill=(255, 255, 255))
        by = ey - rr - 2.4
        if expr == "sad":
            d.line([S(x - 3 * sgn * -1 if False else x - 3, by + (1.6 if sgn < 0 else -.4)), S(x + 3, by + (-.4 if sgn < 0 else 1.6))], fill=hair, width=int(1.5 * k))
        elif expr == "smirk" and i == 1:
            d.line([S(x - 3, by - 1.2), S(x + 3, by - 2.2)], fill=hair, width=int(1.5 * k))
        elif expr == "wow":
            d.arc(S(x - 3.5, by - 2, x + 3.5, by + 3), 200, 340, fill=hair, width=int(1.5 * k))
        else:
            d.line([S(x - 3, by + .4), S(x + 3, by)], fill=hair, width=int(1.5 * k))
    d.arc(S(47.4, 28.5, 52.6, 34), 20, 160, fill=skin2, width=max(1, int(.9 * k)))        # nose
    mx, my = 50, 36.4
    if expr in ("grin", "wink"):
        d.chord(S(mx - 5, my - 2.4, mx + 5, my + 5.5), 0, 180, fill=(120, 30, 40), outline=dark, width=max(1, int(.6 * k)))
        d.chord(S(mx - 4, my - 2, mx + 4, my + 0.6), 0, 180, fill=(255, 255, 255))
    elif expr == "wow":
        d.ellipse(S(mx - 2.4, my - 1.5, mx + 2.4, my + 3.8), fill=(120, 30, 40), outline=dark, width=max(1, int(.6 * k)))
    elif expr == "sad":
        d.arc(S(mx - 4, my - .5, mx + 4, my + 5), 205, 335, fill=dark, width=int(1.2 * k))
    else:
        d.arc(S(mx - 4.5, my - 3, mx + 5, my + 3), 20, 150, fill=dark, width=int(1.2 * k))
    for sgn in (-1, 1):
        d.ellipse(S(50 + sgn * 9.5 - 2.6, 31.5, 50 + sgn * 9.5 + 2.6, 35), fill=(255, 110, 120, 90))
    if st == "beard":
        d.chord(S(37, 24, 63, 50), 10, 170, fill=hair, outline=None)
        d.chord(S(mx - 4.5, my - 2.2, mx + 4.5, my + 4.5), 0, 180, fill=(120, 30, 40))
        d.line([S(mx - 4.5, my - 2.3), S(mx + 4.5, my - 2.3)], fill=hair, width=int(1.8 * k))
    # accessory
    acc = P["acc"]
    if acc == "hardhat":
        d.pieslice(S(33, 0, 67, 30), 180, 360, fill=(255, 205, 40), outline=dark, width=ow)
        d.rounded_rectangle(S(31, 14, 69, 19), int(2.5 * k), fill=(255, 190, 20), outline=dark, width=ow)
        d.rectangle(S(47, 2, 53, 14), fill=(235, 170, 10))
    elif acc == "cap":
        d.pieslice(S(34, 1, 66, 30), 180, 360, fill=th.accent2, outline=dark, width=ow)
        d.rounded_rectangle(S(50, 14, 76, 19), int(2.5 * k), fill=th.accent2, outline=dark, width=ow)
    elif acc == "glasses":
        for sgn in (-1, 1):
            x = ex + sgn * eg
            d.ellipse(S(x - 4.4, ey - 3.6, x + 4.4, ey + 3.6), outline=dark, width=int(1.1 * k))
        d.line([S(ex - eg + 4.4, ey), S(ex + eg - 4.4, ey)], fill=dark, width=int(1 * k))
    out = L.resize((w, h), Image.LANCZOS)
    return out.transpose(Image.FLIP_LEFT_RIGHT) if flip else out


def mascot(th, w=420, pose="wave", expr="grin", acc=None, body=None, color=None, look=(0, 0), flip=False):
    """Default: realistic-style person (th.chars == 'human'); 'blob' gives the cartoon blob characters."""
    kind = getattr(th, "chars", "human")
    if kind == "photo" and getattr(th, "person", None):
        from . import photo
        try:
            return photo.sprite(th, w, pose, expr, flip)
        except Exception as ex:                                   # no key, quota, bad picture: illustrated person instead
            if str(ex) not in photo.FAILED:
                photo.FAILED.append(str(ex))
                print("photo people unavailable, using illustrated people:", str(ex)[:160])
            return person(th, w, pose, expr, flip, look)
    if kind in ("human", "photo") and getattr(th, "person", None):
        return person(th, w, pose, expr, flip, look)
    return blob(th, w, pose, expr, acc, body, color, look, flip)


def with_product(th, prod, h=560, pose="hold", expr="grin"):
    """A person presenting the product (product in the front, at hand height)."""
    if getattr(th, "chars", "human") not in ("human", "photo") or not getattr(th, "person", None):
        return buddy(th, prod, h=h, pose="wave", expr=expr)
    pw_ = int(h * .62)
    ph = h
    ps = mascot(th, pw_, pose if pose in ARMSP else "hold", expr)           # ~1.2 * pw_ tall
    ph_ = ps.height
    target = int(ph * .46)
    pr = prod.resize((max(1, int(prod.width * target / prod.height)), target), Image.LANCZOS)
    wtot = ps.width + int(pr.width * .75)
    H_ = max(ph_, target + 10)
    sp = Image.new("RGBA", (wtot, H_), (0, 0, 0, 0))
    sp.alpha_composite(ps, (0, H_ - ph_))
    px, py = ps.width - int(pr.width * .25), H_ - target - 4
    shadow(sp, pr, (px, py), blur=10, off=(6, 10), a=90)
    sp.alpha_composite(pr, (px, py))
    # hand over the product edge so it looks held
    return sp
