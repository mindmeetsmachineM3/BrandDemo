"""9:16 Reel from the copy: animated text + product pop-ins. Silent by default; optional voice (edge-tts / ElevenLabs) and music."""
import asyncio
import math
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from . import art
from .common import chip, font, fit, mix, ROOT

RW, RH, FPS = 720, 1280, 30

EDGE = {"english": ("en-IN-NeerjaNeural", "en-IN-PrabhatNeural"), "hinglish": ("hi-IN-SwaraNeural", "hi-IN-MadhurNeural"),
        "hindi": ("hi-IN-SwaraNeural", "hi-IN-MadhurNeural"), "marathi": ("mr-IN-AarohiNeural", "mr-IN-ManoharNeural"),
        "bengali": ("bn-IN-TanishaaNeural", "bn-IN-BashkarNeural")}


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def back(x):
    x = max(0.0, min(1.0, x))
    return 1 + 2.70158 * (x - 1) ** 3 + 1.70158 * (x - 1) ** 2


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-500:])
    return r


def dur(p):
    import re
    r = subprocess.run(["ffmpeg", "-i", str(p)], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0


def voice_clip(text, b, out, providers):
    from . import voice as V
    return V.speak(text, b.lang, out, providers)


PATTERNS_BY_SCENE = [None, "sunburst", "dots", "stripes", "blobs"]


def layout_words(th, text, hl, box, start=118, min_size=44):
    """Word positions for a kinetic headline: returns [(word, font, x, y, colour, size)] and bottom y."""
    text = (text or "").strip()
    if not text:
        return [], box[1]
    if th.upper and not any(ord(c) > 0x2000 for c in text):
        text = text.upper()
    x0, y0, x1, y1 = box
    hlw = {art._clean(w) for w in (hl or "").split()} - {""}
    tmp = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    size = start
    while True:
        f = art.dfont(th, size, text)
        sp = tmp.textlength(" ", font=f) * 1.1
        lines, cur, cw = [], [], 0
        for w in text.split():
            ww = tmp.textlength(w, font=f)
            if cur and cw + sp + ww > (x1 - x0):
                lines.append(cur)
                cur, cw = [], 0
            cw += (sp if cur else 0) + ww
            cur.append(w)
        if cur:
            lines.append(cur)
        widths = [sum(tmp.textlength(w, font=f) for w in ln) + sp * (len(ln) - 1) for ln in lines]
        if (len(lines) * size * 1.1 <= y1 - y0 and max(widths) <= x1 - x0) or size <= min_size:
            break
        size -= 4
    out, y = [], y0
    for ln, wd in zip(lines, widths):
        x = x0 + ((x1 - x0) - wd) / 2
        for w in ln:
            out.append((w, f, x, y, th.accent if art._clean(w) in hlw else th.ink, size))
            x += tmp.textlength(w, font=f) + sp
        y += size * 1.1
    return out, y


def word_sprite(th, w, f, col, size):
    pad = int(size * .3)
    tmp = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    ww = int(tmp.textlength(w, font=f)) + 2 * pad
    L = Image.new("RGBA", (ww, int(size * 1.5) + 2 * pad), (0, 0, 0, 0))
    art.draw_word(L, pad, pad, w, f, col, th, th.effect, size)
    return L, pad


def make_scene(b, th, sc, i, n):
    """Everything one scene needs, pre-rendered once."""
    rng = random.Random(th.seed + i)
    kind = PATTERNS_BY_SCENE[i % 5] or th.pattern
    bg = art.background(th, RW, RH, kind, rng)
    words, ybot = layout_words(th, sc.get("text", ""), sc.get("highlight", ""), (40, 175, RW - 40, 175 + 360), start=120 if i else 140)
    sprites = [(w, *word_sprite(th, w, f, col, size), x, y, size) for (w, f, x, y, col, size) in words]
    prods = sc.get("products") or []
    pr = b.product(prods[0]) if prods else None
    last = i == n - 1
    pose, expr = [("wave", "grin"), ("shrug", "sad"), ("point", "wow"), ("cheer", "wink"), ("cheer", "grin")][i % 5]
    if pr is not None:
        sp = art.with_product(th, pr, h=520, pose=pose if pose in ("point", "cheer", "hold") else "hold", expr=expr)
    else:
        sp = art.mascot(th, 420, pose, expr, flip=(i % 2 == 1))
    s = min(430 / sp.height, 600 / sp.width) if sp.height > 430 else 1
    sp = sp.resize((int(sp.width * s), int(sp.height * s)), Image.LANCZOS) if s != 1 else sp
    sub = sc.get("sub", "")
    subimg = None
    if sub:
        tmp = ImageDraw.Draw(Image.new("RGB", (4, 4)))
        fs, sl, slh = fit(tmp, sub, "Bold", RW - 160, 130, 38, 24, 1.2)
        wmax = int(max(tmp.textlength(l, font=fs) for l in sl)) + 56
        hh = len(sl) * slh + 30
        subimg = Image.new("RGBA", (wmax + 20, hh + 20), (0, 0, 0, 0))
        art.rrect(subimg, (10, 10, 10 + wmax, 10 + hh), 22, th.card, th.dark, 4, shadow=5)
        d = ImageDraw.Draw(subimg)
        yy = 10 + 15
        for ln in sl:
            d.text((10 + wmax / 2, yy), ln, font=fs, fill=th.card_ink, anchor="ma")
            yy += slh
    sparks = [(rng.randint(40, RW - 40), rng.randint(180, RH - 200), rng.randint(14, 30), rng.random() * 6) for _ in range(6)]
    return dict(bg=bg, words=sprites, ybot=ybot, sp=sp, sub=subimg, sparks=sparks, i=i, last=last, kind=kind)


def frame(b, th, S, t, T, n, logo_chip):
    img = S["bg"].copy()
    i = S["i"]
    d = ImageDraw.Draw(img)
    # twinkles
    for (x, y, r, ph) in S["sparks"]:
        k = .5 + .5 * math.sin(t * 5 + ph)
        art.sparkle(img, x, y, int(r * (.5 + .5 * k)), th.accent if (x // 7) % 2 else (255, 255, 255, 200))
    img.alpha_composite(logo_chip, (30, 34))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, RW, 8), fill=(0, 0, 0, 90))
    d.rectangle((0, 0, int(RW * (i + min(1, t / T)) / n), 8), fill=th.accent)
    # sprite: slides in from the side, then bobs
    sp = S["sp"]
    a = ease((t - .15) / .55)
    side = -1 if i % 2 else 1
    bx = RW / 2 + side * (RW * .5) * (1 - a) + (RW * .12 * side if sp.width < RW * .6 else 0)
    bob = 10 * math.sin(t * 3.2)
    by = RH - 150 + bob
    sc_ = 1 + .04 * math.sin(t * 3.2 + 1)
    spr = sp.resize((int(sp.width * sc_), int(sp.height * sc_)), Image.LANCZOS) if abs(sc_ - 1) > .005 else sp
    spr = spr.rotate(3 * math.sin(t * 2.4), resample=Image.BICUBIC, expand=True)
    art.burst(img, int(bx), int(by - sp.height / 2), int(min(300, sp.height * .62) * ease((t - .1) / .5)), art.mix(th.bg2, (255, 255, 255), .22), th.dark, n=18, depth=.08, ow=0) if ease((t - .1) / .5) > .05 else None
    img.alpha_composite(spr, (int(bx - spr.width / 2), int(by - spr.height)))
    # kinetic words
    for k, (w, L, pad, x, y, size) in enumerate(S["words"]):
        s = back((t - .08 - k * .13) / .32)
        if s <= .02:
            continue
        ww, hh = L.size
        q = L.resize((max(1, int(ww * s)), max(1, int(hh * s))), Image.LANCZOS)
        cx, cy = x - pad + ww / 2, y - pad + hh / 2
        img.alpha_composite(q, (int(cx - q.width / 2), int(cy - q.height / 2)))
    # sub card
    if S["sub"] is not None:
        a2 = ease((t - .55) / .35)
        if a2 > 0:
            sb = S["sub"]
            y = int(S["ybot"] + 24 + (1 - a2) * 40)
            if a2 < 1:
                sb = sb.copy()
                sb.putalpha(sb.split()[3].point(lambda v: int(v * a2)))
            img.alpha_composite(sb, (int(RW / 2 - sb.width / 2), y))
    # footer band
    d = ImageDraw.Draw(img)
    d.rectangle((0, RH - 100, RW, RH), fill=th.dark)
    d.rectangle((0, RH - 100, RW, RH - 94), fill=b.primary)
    d.text((34, RH - 46), b.phone or b.tagline or b.name, font=font("Bold", 30, b.phone or b.tagline), fill=(255, 255, 255), anchor="lm")
    if b.handle:
        d.text((RW - 34, RH - 46), "@" + b.handle, font=font("Bold", 30), fill=th.accent if abs(art.lum(th.accent) - art.lum(th.dark)) > 90 else (255, 255, 255), anchor="rm")
    fa = 1 - ease(t / .14)
    if fa > 0:
        img.alpha_composite(Image.new("RGBA", (RW, RH), (255, 255, 255, int(150 * fa))))
    return img.convert("RGB")


def build_reel(b, reel, out_path, th, voice="auto", scene_min=3.0):
    from . import voice as V
    providers = V.chain(voice if voice != "none" else "auto")
    scenes = reel["scenes"]
    n = len(scenes)
    tmp = Path(tempfile.mkdtemp(prefix="reel_"))
    # logo chip once
    chipimg = Image.new("RGBA", (RW, 160), (0, 0, 0, 0))
    chip(chipimg, b, x=0, y=0, w=150)
    chipimg = chipimg.crop((0, 0, 190, 100))
    durs, clips = [], []
    for i, sc in enumerate(scenes):
        d_ = scene_min + 0.6 * (len(sc.get("text", "")) > 28)
        if voice != "none" and sc.get("say"):
            try:
                c = tmp / f"v{i}.mp3"
                used, label = voice_clip(sc["say"], b, c, providers)
                providers = [used] + [p for p in providers if p != used]       # keep the voice that worked, same voice for the whole Reel
                voice = label
                d_ = max(d_, dur(c) + .5)
                clips.append((i, c))
            except Exception as ex:
                print("voice failed, reel stays silent:", str(ex)[:150], file=sys.stderr)
                clips, voice = [], "none"
        durs.append(d_)
    layers = [make_scene(b, th, sc, i, n) for i, sc in enumerate(scenes)]
    total = sum(durs)
    # audio track
    audio = None
    if clips:
        parts = []
        for i, sc in enumerate(scenes):
            w = tmp / f"s{i}.wav"
            src = next((c for j, c in clips if j == i), None)
            if src:
                run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", f"adelay=300|300,apad", "-t", f"{durs[i]:.3f}", "-ar", "44100", "-ac", "1", str(w)])
            else:
                run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{durs[i]:.3f}", str(w)])
            parts.append(w)
        lst = tmp / "l.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        audio = tmp / "voice.wav"
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", str(audio)])
    music = sorted((ROOT / "assets" / "music").glob("*.mp3")) if (ROOT / "assets" / "music").exists() else []
    if not music and os.getenv("REEL_MUSIC", "on") != "off":          # no licensed track supplied: use an original generated beat
        from . import music as M
        gen = tmp / "beat.wav"
        M.track(total + 1, th.seed, gen)
        music = [gen]
    if music:
        m = random.choice(music)
        mixed = tmp / "mix.wav"
        if audio:
            run(["ffmpeg", "-v", "error", "-y", "-i", str(audio), "-stream_loop", "-1", "-i", str(m), "-filter_complex",
                 "[1:a]volume=0.16[m];[0:a][m]amix=inputs=2:duration=first:normalize=0", "-ar", "44100", str(mixed)])
        else:
            run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", str(m), "-t", f"{total:.2f}", "-af", "volume=0.35,afade=t=out:st=%.2f:d=1" % (total - 1), "-ar", "44100", str(mixed)])
        audio = mixed
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}", "-r", str(FPS), "-i", "-"]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
    cmd += (["-c:a", "aac", "-b:a", "160k", "-shortest"] if audio else ["-an"])
    cmd += ["-movflags", "+faststart", str(out_path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i, sc in enumerate(scenes):
        frames = int(durs[i] * FPS)
        for f in range(frames):
            fr = frame(b, th, layers[i], f / FPS, durs[i], n, chipimg)
            p.stdin.write(fr.tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg failed")
    return total, ("voice: " + voice if clips else "no voice (voice service failed or off)") + (", music" if music else "")
