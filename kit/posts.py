"""Feed posts and carousel slides, themed from brand.json colours."""
from PIL import Image, ImageDraw

from .common import (chip, draw_lines, fit, font, footer, mix, pill, place, products_row, text_fit)

W = 1080


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def on(c):
    """readable text colour on background c"""
    return (24, 24, 24) if lum(c) > 150 else (255, 255, 255)


def canvas(b, bg):
    return Image.new("RGBA", (W, b.post_h), bg + (255,))


def hero(b, p):
    H = b.post_h
    bg = b.secondary
    img = canvas(b, bg)
    d = ImageDraw.Draw(img)
    d.ellipse((int(W * .55), int(H * .30), int(W * 1.35), int(H * .95)), fill=mix(bg, (0, 0, 0), .10))
    chip(img, b)
    ink = on(bg)
    hl = b.primary if abs(lum(b.primary) - lum(bg)) > 60 else ink
    d.text((44, 176), (p.get("eyebrow") or "").upper(), font=font("Bold", 27, p.get("eyebrow", "")), fill=hl)
    y = text_fit(d, 44, 222, p.get("headline", ""), "Bold", 990, 170, 70, ink, lh=1.12)
    y = text_fit(d, 44, y + 4, p.get("highlight", ""), "Bold", 990, 130, 92, hl, lh=1.1) if p.get("highlight") else y
    top = int(y + 24)
    bottom = H - 100
    wide = sum(b.product(i).width / b.product(i).height for i in p["products"]) > 1.15     # squat packs (tubs, buckets): full-width band
    if wide:
        d = ImageDraw.Draw(img)
        yb = text_fit(d, 44, top + 6, p.get("body", ""), "Medium", 990, 120, 32, ink, lh=1.35)
        products_row(img, b, p["products"], (40, int(yb + 16), W - 40, bottom - (90 if p.get("cta") else 12)))
    else:
        products_row(img, b, p["products"], (int(W * .50), top, W - 30, bottom - 20))
        d = ImageDraw.Draw(img)
        yb = text_fit(d, 44, top + 10, p.get("body", ""), "Medium", 450, 260, 32, ink, lh=1.38)
    if p.get("cta"):
        pill(img, 44, H - 175, p["cta"], b.primary, on(b.primary), size=26)
    if p.get("badge"):
        cx, cy, r = W - 170, top + 60, 105
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=b.primary, outline=(255, 255, 255), width=5)
        text_fit(d, cx, cy - 36, p["badge"], "Bold", 170, 90, 44, on(b.primary), lh=1.05, center=True)
    footer(img, b)
    return img


def offer(b, p):
    H = b.post_h
    bg = b.primary
    img = canvas(b, bg)
    d = ImageDraw.Draw(img)
    for i in range(14, 0, -1):                                   # soft spotlight behind the products
        r = int(220 + i * 38)
        d.ellipse((W / 2 - r, H * .62 - r, W / 2 + r, H * .62 + r), fill=mix(bg, (255, 255, 255), .035 * (15 - i) / 14 * 4))
    chip(img, b)
    ink = on(bg)
    acc = b.secondary
    d.text((W / 2, 180), (p.get("eyebrow") or "").upper(), font=font("Bold", 27, p.get("eyebrow", "")), fill=acc, anchor="ma")
    y = text_fit(d, W / 2, 224, p.get("headline", ""), "Bold", 940, 220, 84, ink, lh=1.1, center=True)
    if p.get("highlight"):
        y = text_fit(d, W / 2, y + 2, p["highlight"], "Bold", 940, 120, 84, acc, lh=1.1, center=True)
    y = text_fit(d, W / 2, y + 12, p.get("body", ""), "Medium", 820, 110, 32, ink, lh=1.3, center=True)
    products_row(img, b, p["products"], (60, int(y + 40), W - 60, H - 200))
    d = ImageDraw.Draw(img)
    if p.get("badge"):
        cx, cy, r = W - 190, int(y + 150), 115
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=acc, outline=(255, 255, 255), width=6)
        text_fit(d, cx, cy - 38, p["badge"], "Bold", 190, 100, 50, on(acc), lh=1.05, center=True)
    if p.get("cta"):
        f = font("Bold", 28, p["cta"])
        w = int(d.textlength(p["cta"], font=f)) + 60
        pill(img, (W - w) // 2, H - 172, p["cta"], acc, on(acc), size=28)
    footer(img, b)
    return img


def tips(b, p):
    H = b.post_h
    bg = b.dark
    img = canvas(b, bg)
    d = ImageDraw.Draw(img)
    d.ellipse((-260, int(H * .55), 520, int(H * 1.1)), fill=mix(bg, b.primary, .35))
    chip(img, b)
    ink = on(bg)
    d.text((44, 184), (p.get("eyebrow") or "").upper(), font=font("Bold", 27, p.get("eyebrow", "")), fill=b.secondary)
    y = text_fit(d, 44, 226, p.get("headline", ""), "Bold", 700, 190, 80, ink, lh=1.1)
    if p.get("highlight"):
        y = text_fit(d, 44, y, p["highlight"], "Bold", 700, 110, 80, b.secondary, lh=1.1)
    items = p.get("items", [])[:3]
    top = int(y + 36)
    avail = H - 190 - top
    n = max(1, len(items))
    gap = 18
    ch = min(190, int((avail - gap * (n - 1)) / n))
    products_row(img, b, p["products"], (690, 300, W - 20, H - 120))
    d = ImageDraw.Draw(img)
    yy = top
    for i, it in enumerate(items, 1):
        d.rounded_rectangle((44, yy, 650, yy + ch), 30, fill=(255, 255, 255))
        r = min(40, ch // 2 - 14)
        d.ellipse((66, yy + ch / 2 - r, 66 + 2 * r, yy + ch / 2 + r), fill=b.primary)
        d.text((66 + r, yy + ch / 2), str(i), font=font("Bold", int(r * 1.1)), fill=on(b.primary), anchor="mm")
        tx = 66 + 2 * r + 22
        if it.get("body"):
            text_fit(d, tx, yy + 16, it.get("title", ""), "Bold", 650 - tx - 20, ch * .4, 32, (24, 24, 24), lh=1.1)
            text_fit(d, tx, yy + 16 + ch * .38, it["body"], "Medium", 650 - tx - 20, ch * .5, 25, (80, 80, 80), lh=1.2)
        else:
            text_fit(d, tx, yy + ch / 2 - 22, it.get("title", ""), "Bold", 650 - tx - 20, ch * .7, 34, (24, 24, 24), lh=1.15)
        yy += ch + gap
    if p.get("note"):
        d.text((44, H - 125), p["note"], font=font("Medium", 23, p["note"]), fill=mix(bg, (255, 255, 255), .7), anchor="lm")
    footer(img, b, fill=mix(bg, (0, 0, 0), .35))
    return img


KINDS = {"hero": hero, "offer": offer, "tips": tips}


def post(b, p):
    return KINDS.get(p.get("kind"), hero)(b, p).convert("RGB")


# ------------------------------------------------------------------ carousel
def car_cover(b, c):
    H = b.post_h
    bg = b.primary
    img = canvas(b, bg)
    d = ImageDraw.Draw(img)
    d.ellipse((-200, int(H * .45), W + 200, int(H * 1.25)), fill=mix(bg, (0, 0, 0), .18))
    chip(img, b)
    ink = on(bg)
    d.text((44, 176), (c.get("eyebrow") or "").upper(), font=font("Bold", 27, c.get("eyebrow", "")), fill=b.secondary)
    y = text_fit(d, 44, 222, c.get("headline", ""), "Bold", 990, 260, 96, ink, lh=1.08)
    if c.get("highlight"):
        y = text_fit(d, 44, y + 4, c["highlight"], "Bold", 990, 150, 96, b.secondary, lh=1.08)
    products_row(img, b, c["products"], (80, int(y + 30), W - 80, H - 190))
    pill(img, 44, H - 172, "Swipe  >>", b.secondary, on(b.secondary), size=28)
    footer(img, b, fill=mix(b.dark, b.primary, .2))
    return img.convert("RGB")


def car_slide(b, s, i, n):
    H = b.post_h
    bg = b.light
    img = canvas(b, bg)
    d = ImageDraw.Draw(img)
    chip(img, b)
    d.ellipse((W - 330, 40, W - 30, 340), fill=mix(bg, b.primary, .12))
    d.ellipse((50, 190, 190, 330), fill=b.primary)
    d.text((120, 260), str(i), font=font("Bold", 84), fill=on(b.primary), anchor="mm")
    y = text_fit(d, 44, 380, s.get("title", ""), "Bold", 990, 260, 76, b.dark, lh=1.12)
    if s.get("body"):
        y = text_fit(d, 44, y + 12, s["body"], "Medium", 520 if s["products"] else 990, 330, 38, (60, 60, 60), lh=1.42)
    if s.get("products"):
        products_row(img, b, s["products"], (560, int(H * .40), W - 10, H - 100))
    for k in range(n):
        d.ellipse((44 + k * 34, H - 120, 44 + k * 34 + 18, H - 102), fill=b.primary if k == i else mix(bg, (0, 0, 0), .2))
    footer(img, b)
    return img.convert("RGB")


def car_cta(b, c):
    H = b.post_h
    bg = b.dark
    img = canvas(b, bg)
    d = ImageDraw.Draw(img)
    d.ellipse((-200, int(H * .55), W + 200, int(H * 1.3)), fill=mix(bg, b.primary, .4))
    chip(img, b, x=44, y=40)
    y = text_fit(d, W / 2, 300, c.get("headline", ""), "Bold", 940, 260, 90, (255, 255, 255), lh=1.1, center=True)
    y = text_fit(d, W / 2, y + 16, c.get("body", ""), "Medium", 860, 200, 40, mix(bg, (255, 255, 255), .8), lh=1.35, center=True)
    if b.phone:
        f = font("Bold", 38)
        w = int(d.textlength(b.phone, font=f)) + 70
        pill(img, (W - w) // 2, int(y + 40), b.phone, b.secondary, on(b.secondary), size=38, pady=16)
    if b.handle:
        d.text((W / 2, int(y + 190)), "@" + b.handle, font=font("Bold", 34), fill=b.secondary, anchor="ma")
    footer(img, b, fill=mix(bg, (0, 0, 0), .35))
    return img.convert("RGB")


def carousel(b, c):
    slides = [car_cover(b, c["cover"])]
    body = c["slides"][:3]
    for i, s in enumerate(body, 1):
        slides.append(car_slide(b, s, i, len(body) + 1))
    slides.append(car_cta(b, c["cta"]))
    return slides
