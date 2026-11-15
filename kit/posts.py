"""Feed posts + carousel. Five layout families, each drawn in a fresh theme with original mascots."""
import random

from PIL import Image, ImageDraw

from . import art
from .art import lum, on, rrect, burst, sparkle, squiggle, bubble, rich, mascot, buddy, with_product
from .common import chip, fit, font, text_fit, place, shadow

W = 1080
KINDS = ["mascot_hero", "quote_poster", "split_poster", "comic_duo", "list_cards"]


# ------------------------------------------------------------------ helpers
def start(b, th, rng, kind=None):
    H = b.post_h
    img = art.background(th, W, H, kind, rng)
    return img, H


def foot(img, b, th, h=76):
    W_, H = img.size
    d = ImageDraw.Draw(img)
    d.rectangle((0, H - h, W_, H), fill=th.dark)
    d.rectangle((0, H - h, W_, H - h + 6), fill=b.primary)
    d.text((44, H - h // 2 + 3), b.tagline or b.name, font=font("Bold", 26, b.tagline), fill=(255, 255, 255), anchor="lm")
    if b.handle:
        d.text((W_ - 44, H - h // 2 + 3), "@" + b.handle, font=font("Bold", 26), fill=th.accent if abs(lum(th.accent) - lum(th.dark)) > 90 else (255, 255, 255), anchor="rm")


def cta_pill(img, th, text, cx, y, size=30, rot=0):
    if not text:
        return
    d = ImageDraw.Draw(img)
    f = font("Bold", size, text)
    w = int(d.textlength(text, font=f)) + 80
    rrect(img, (cx - w / 2, y, cx + w / 2, y + size + 40), (size + 40) // 2, th.accent, th.dark, 5, shadow=7, rot=rot)
    ImageDraw.Draw(img).text((cx, y + (size + 40) / 2 + 1), text, font=f, fill=on(th.accent), anchor="mm")


def tag(img, th, text, x, y, fill=None, size=26, rot=0):
    fill = fill or th.dark
    d = ImageDraw.Draw(img)
    f = font("Bold", size, text)
    w = int(d.textlength(text, font=f)) + 44
    rrect(img, (x, y, x + w, y + size + 22), 14, fill, shadow=0, rot=rot)
    d = ImageDraw.Draw(img)
    d.text((x + w / 2, y + (size + 22) / 2 + 1), text, font=f, fill=on(fill), anchor="mm")
    return x + w


def fit_sprite(sp, maxw, maxh):
    s = min(maxw / sp.width, maxh / sp.height)
    return sp.resize((max(1, int(sp.width * s)), max(1, int(sp.height * s))), Image.LANCZOS)


def put(img, sp, cx, bottom, ground_shadow=True):
    if ground_shadow:
        art.shadow_under(img, cx, bottom - 8, sp.width * .7)
    img.alpha_composite(sp, (int(cx - sp.width / 2), int(bottom - sp.height)))


def stamp(img, th, text, cx, cy, r=105, rot=-12):
    if not text:
        return
    burst(img, cx, cy, r, th.accent2 if lum(th.accent2) > 60 and abs(lum(th.accent2) - lum(th.bg)) > 40 else th.accent, th.dark, n=13, rot=.3)
    fillc = th.accent2 if lum(th.accent2) > 60 and abs(lum(th.accent2) - lum(th.bg)) > 40 else th.accent
    rich(img, th, text, "", (cx - r * .72, cy - r * .5, cx + r * .72, cy + r * .5), start=54, min_size=22, fill=on(fillc), effect="plain", rot=rot, lh=1.0)


def other(th):
    """a second, different person in the same colours (so two characters in one picture never look identical)"""
    import dataclasses
    rng = random.Random(th.seed + 7)
    cur = th.person["role"]
    pool = [r for r in art.ROLES if r[0] != cur and (cur in ("painter", "engineer") or r[0] not in ("painter", "engineer"))]
    pr = art.make_person(rng, [th.accent, th.accent2, th.card, (255, 255, 255)], th.bg, role=rng.choice(pool))
    return dataclasses.replace(th, person=pr)


def head(p):
    return p.get("punch") or p.get("headline") or ""


def prod_ids(p, b):
    return p.get("products") or b.product_ids()[:1]


def hero_buddy(b, th, p, h, pose, expr):
    return with_product(th, b.product(prod_ids(p, b)[0]), h=h, pose=pose, expr=expr)


# ------------------------------------------------------------------ layouts
def mascot_hero(b, p, th, rng):
    img, H = start(b, th, rng)
    chip(img, b)
    cy = int(H * .62)
    art.burst(img, 400, cy + 20, 320, art.mix(th.bg2, (255, 255, 255), .22), th.dark, n=18, depth=.08, ow=0)
    y = rich(img, th, head(p), p.get("highlight", ""), (50, 150, W - 50, 150 + int(H * .27)), start=140, rot=-2)
    bd = hero_buddy(b, th, p, int(H * .40), "wave", rng.choice(["grin", "wow", "wink"]))
    bd = fit_sprite(bd, 600, int(H * .56))
    put(img, bd, 400, H - 215)
    m = mascot(other(th), 300, rng.choice(["point", "cheer", "wave"]), rng.choice(["grin", "wink", "smirk"]), flip=True)
    put(img, m, 900, H - 175)
    if p.get("bubble"):
        bubble(img, th, p["bubble"], 800, y + 110, 440, tail=(880, H - 175 - 360 + 40), start=40, maxh=180, rot=-2)
    stamp(img, th, p.get("sticker") or p.get("stamp", ""), 150, cy - 170)
    cta_pill(img, th, p.get("cta", ""), 540, H - 170 if H > 1200 else H - 150)
    foot(img, b, th)
    return img


def quote_poster(b, p, th, rng):
    img, H = start(b, th, rng)
    chip(img, b)
    d = ImageDraw.Draw(img)
    q = p.get("quote") or head(p)
    sparkle(img, 120, 285, 46, th.accent)
    sparkle(img, W - 110, 250, 30, th.accent2)
    y = rich(img, th, q, p.get("highlight", ""), (60, 230, W - 60, int(H * .54)), start=230, min_size=60, lh=1.08, rot=-1.5)
    squiggle(img, 200, y + 40, 520, th.accent, amp=11, w=9)
    d = ImageDraw.Draw(img)
    d.text((60, y + 78), "- " + b.name, font=font("Bold", 30, b.name), fill=th.ink, anchor="la")
    pid = prod_ids(p, b)
    pr = b.product(pid[0])
    ph = int(H * .27)
    pw = int(pr.width * ph / pr.height)
    if pw > 420:
        ph, pw = int(ph * 420 / pw), 420
    place(img, pr, W - pw - 60, H - 110 - ph - 20, h=ph, rot=7)
    m = mascot(th, 290, rng.choice(["cheer", "shrug", "wave"]), rng.choice(["wow", "grin", "wink"]))
    put(img, m, 200, H - 95)
    if p.get("sticker"):
        stamp(img, th, p["sticker"], W - 150, int(H * .60) + 40, r=95, rot=10)
    cta_pill(img, th, p.get("cta", ""), 640, H - 175, size=26, rot=-2) if p.get("cta") and H > 1200 else None
    foot(img, b, th)
    return img


def split_poster(b, p, th, rng):
    img, H = start(b, th, rng)
    d = ImageDraw.Draw(img)
    top = int(H * .44)
    poly = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
    ImageDraw.Draw(poly).polygon([(0, (top + 70) * 2), (W * 2, (top - 70) * 2), (W * 2, H * 2), (0, H * 2)], fill=th.card)
    poly = poly.resize((W, H), Image.LANCZOS)
    img.alpha_composite(poly)
    chip(img, b)
    ImageDraw.Draw(img)
    tag(img, th, p.get("before_tag", "BEFORE"), 50, 160)
    rich(img, th, p.get("problem") or "Still struggling?", "", (50, 220, 700, top + 20), start=110, min_size=44, align="left", rot=-2)
    m = mascot(other(th), 290, "shrug", "sad", flip=True)
    put(img, m, 880, top + 30, ground_shadow=False)
    tag(img, th, "WITH " + b.name.upper(), 50, top + 110, fill=th.accent2 if abs(lum(th.accent2) - lum(th.card)) > 60 else th.dark)
    rich(img, th, p.get("solution") or head(p), p.get("highlight", ""), (50, top + 175, 640, H - 180), start=96, min_size=42, align="left",
         fill=th.card_ink, hlfill=th.bg if abs(lum(th.bg) - lum(th.card)) > 70 else th.accent2, effect="plain" if th.effect != "sticker" else "plain")
    bd = hero_buddy(b, th, p, int(H * .36), "cheer", "grin")
    bd = fit_sprite(bd, 520, int(H * .42))
    put(img, bd, 830, H - 100)
    stamp(img, th, p.get("sticker", ""), 930, top + 150, r=88, rot=12)
    cta_pill(img, th, p.get("cta", ""), 330, H - 160, size=26) if H > 1200 else None
    foot(img, b, th)
    return img


def comic_duo(b, p, th, rng):
    img, H = start(b, th, rng, kind="halftone")
    chip(img, b)
    pad = 36
    box = (pad, 150, W - pad, H - 110)
    rrect(img, box, 34, th.card, th.dark, 7, shadow=10)
    burst(img, 560, int(H * .56), 360, art.mix(th.card, th.accent, .35), th.card, n=22, depth=.07, ow=0)
    ImageDraw.Draw(img)
    x = tag(img, th, p.get("eyebrow") or "MEANWHILE...", box[0] + 22, box[1] + 20, fill=th.accent, size=26)
    m = mascot(other(th), 270, rng.choice(["shrug", "point", "wave"]), rng.choice(["wow", "smirk", "sad"]), flip=True)
    put(img, m, 850, int(H * .50))
    bubble(img, th, p.get("problem") or p.get("bubble") or "Kya karein?", 410, 350, 580, tail=(770, int(H * .50) - 250), start=50, maxh=200, rot=-2)
    bd = hero_buddy(b, th, p, int(H * .30), "point", "wink")
    bd = fit_sprite(bd, 430, int(H * .33))
    put(img, bd, 270, H - 175)
    bubble(img, th, p.get("bubble") or head(p), 745, int(H * .66), 500, tail=(420, H - 175 - bd.height + 60), start=52, maxh=250,
           fill=th.accent, ink=on(th.accent), rot=1.5)
    cta_pill(img, th, p.get("cta", ""), 760, H - 175, size=24, rot=-2) if p.get("cta") else None
    foot(img, b, th)
    return img


def list_cards(b, p, th, rng):
    img, H = start(b, th, rng)
    chip(img, b)
    y = rich(img, th, head(p), p.get("highlight", ""), (50, 150, W - 50, 150 + int(H * .20)), start=116, min_size=50, rot=-1.5)
    items = (p.get("items") or [])[:3]
    n = max(1, len(items))
    top = int(y + 40)
    avail = H - 130 - top
    gap = 22
    ch = min(220, int((avail - gap * (n - 1)) / n))
    yy = top
    for i, it in enumerate(items):
        t = it.get("title", "") if isinstance(it, dict) else str(it)
        rot = (-1.8, 1.2, -1.0)[i % 3]
        rrect(img, (50, yy, 690, yy + ch), 28, th.card, th.dark, 5, shadow=9, rot=rot)
        burst(img, 120, yy + ch / 2, ch * .3, th.accent, th.dark, n=10, depth=.14, ow=4)
        d = ImageDraw.Draw(img)
        d.text((120, yy + ch / 2 + 2), str(i + 1), font=art.dfont(th, int(ch * .34), "1"), fill=on(th.accent), anchor="mm")
        f_, ln_, lh_ = fit(d, t, "Bold", 470, ch - 40, 60, 26, 1.12)
        y_ = yy + (ch - len(ln_) * lh_) / 2
        for l_ in ln_:
            d.text((190, y_), l_, font=f_, fill=th.card_ink)
            y_ += lh_
        yy += ch + gap
    bd = hero_buddy(b, th, p, int(H * .40), "wave", "grin")
    bd = fit_sprite(bd, 380, int(H * .40))
    put(img, bd, 870, int(top + avail * .62))
    m = mascot(other(th), 230, "cheer", "wink", flip=True)
    put(img, m, 900, H - 95)
    stamp(img, th, p.get("sticker", ""), 900, top + 40, r=80, rot=-10)
    foot(img, b, th)
    return img


LAYOUT = {"mascot_hero": mascot_hero, "quote_poster": quote_poster, "split_poster": split_poster, "comic_duo": comic_duo, "list_cards": list_cards}


def post(b, p, th, rng, kind):
    return LAYOUT[kind](b, p, th, rng).convert("RGB")


# ------------------------------------------------------------------ carousel (one theme, one character, different poses)
def _char(th, rng):
    return dict(body=th.body, acc=th.acc, color=th.char_col)


def car_cover(b, c, th, rng):
    img, H = start(b, th, rng)
    chip(img, b)
    art.burst(img, 540, int(H * .70), 330, art.mix(th.bg2, (255, 255, 255), .2), th.dark, n=20, depth=.07, ow=0)
    y = rich(img, th, head(c), c.get("highlight", ""), (50, 160, W - 50, 160 + int(H * .30)), start=170, min_size=70, rot=-2)
    bd = with_product(th, b.product(prod_ids(c, b)[0]), h=int(H * .4), pose="cheer", expr="grin")
    put(img, fit_sprite(bd, 640, int(H * .5)), 440, H - 175)
    put(img, mascot(other(th), 300, "point", "wink", flip=True), 920, H - 150)
    cta_pill(img, th, "SWIPE  >>", 540, H - 150 if H < 1200 else H - 168, size=30, rot=-2)
    foot(img, b, th)
    return img


def car_slide(b, s, i, n, th, rng):
    img, H = start(b, th, rng, kind=["dots", "stripes", "blobs", "zigzag"][i % 4])
    chip(img, b)
    d = ImageDraw.Draw(img)
    burst(img, 150, 320, 95, th.accent, th.dark, n=12, ow=6, rot=.2)
    ImageDraw.Draw(img).text((150, 324), str(i), font=art.dfont(th, 110, "1"), fill=on(th.accent), anchor="mm")
    y = rich(img, th, s.get("title", ""), s.get("highlight", ""), (60, 420, 720, 420 + int(H * .24)), start=150, min_size=56, align="left", rot=-1)
    if s.get("body"):
        rrect(img, (50, y + 30, 640, y + 30 + min(330, int(H * .26))), 26, th.card, th.dark, 5, shadow=8)
        text_fit(ImageDraw.Draw(img), 82, y + 54, s["body"], "Medium", 530, min(330, int(H * .26)) - 50, 36, th.card_ink, min_size=24, lh=1.3)
    poses = [("wave", "grin"), ("hold", "wow"), ("cheer", "wink")][(i - 1) % 3]
    if s.get("products"):
        bd = with_product(th, b.product(s["products"][0]), h=int(H * .32), pose=poses[0], expr=poses[1])
        put(img, fit_sprite(bd, 560, int(H * .44)), 800, H - 110)
    else:
        put(img, mascot(th, 470, *poses), 810, H - 100)
    for k in range(n):
        ImageDraw.Draw(img).ellipse((50 + k * 34, H - 130, 68 + k * 34, H - 112), fill=th.accent if k == i else (255, 255, 255, 120))
    foot(img, b, th)
    return img


def car_cta(b, c, th, rng):
    img, H = start(b, th, rng)
    chip(img, b)
    y = rich(img, th, head(c), c.get("highlight", ""), (50, 200, W - 50, 200 + int(H * .25)), start=150, min_size=60, rot=-2)
    put(img, mascot(th, 380, "cheer", "grin"), 540, int(H * .77))
    d = ImageDraw.Draw(img)
    if c.get("body"):
        text_fit(d, W / 2, y + 20, c["body"], "Bold", 860, 120, 38, th.ink, min_size=24, center=True)
    if b.phone:
        cta_pill(img, th, b.phone, 540, int(H * .78) + 20, size=40)
    if b.handle:
        d.text((540, int(H * .78) + 120), "@" + b.handle, font=font("Bold", 34), fill=th.accent, anchor="ma")
    foot(img, b, th)
    return img


def carousel(b, c, ths, rngs):
    """ths: list of 1 theme (shared by all slides)."""
    th, rng = ths[0], rngs[0]
    slides = [car_cover(b, c["cover"], th, random.Random(th.seed))]
    body = c["slides"][:3]
    for i, s in enumerate(body, 1):
        slides.append(car_slide(b, s, i, len(body) + 1, th, random.Random(th.seed + i)))
    slides.append(car_cta(b, c["cta"], th, random.Random(th.seed + 9)))
    return [s.convert("RGB") for s in slides]
