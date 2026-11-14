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

from .common import chip, font, fit, mix, ROOT
from .posts import lum, on

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


def voice_clip(text, b, out, provider):
    if provider == "edge":
        import edge_tts
        v = os.getenv("EDGE_VOICE") or EDGE.get(b.lang, EDGE["english"])[0]
        asyncio.run(edge_tts.Communicate(text, v, rate="+6%").save(str(out)))
    elif provider == "elevenlabs":
        import requests
        vid, key = os.environ["ELEVEN_VOICE"], os.environ["ELEVEN_API_KEY"]
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128", headers={"xi-api-key": key},
                          json={"text": text, "model_id": os.getenv("ELEVEN_MODEL") or "eleven_multilingual_v2"}, timeout=90)
        r.raise_for_status()
        Path(out).write_bytes(r.content)
    else:
        raise RuntimeError("unknown voice provider " + provider)


def scene_layers(b, sc, i, n, last):
    """Pre-resize everything one scene needs."""
    prods = [b.product(p) for p in sc.get("products", [])][:3]
    ph = int(RH * (0.42 if len(prods) < 2 else 0.36))
    pl = []
    for im in prods:
        h = ph
        w = int(im.width * h / im.height)
        if w > RW * (0.8 / max(1, len(prods))) * (1.1 if len(prods) == 1 else 1):
            w = int(RW * 0.8 / max(1, len(prods)))
            h = int(im.height * w / im.width)
        pl.append(im.resize((max(1, w), max(1, h)), Image.LANCZOS))
    return pl


def frame(b, sc, t, T, idx, n, layers, logo_chip):
    bgA, bgB = (b.primary, b.dark) if idx % 2 == 0 else (b.dark, b.primary)
    img = Image.new("RGBA", (RW, RH))
    d = ImageDraw.Draw(img)
    for y in range(0, RH, 4):                                      # vertical gradient
        d.rectangle((0, y, RW, y + 4), fill=mix(bgA, bgB, y / RH * .85))
    if layers:
        gr = ease((t - .2) / .6)
        d.ellipse((RW / 2 - 270 * gr, RH * .66 - 270 * gr, RW / 2 + 270 * gr, RH * .66 + 270 * gr), fill=mix(bgA, (255, 255, 255), .09))
    ink = (255, 255, 255)
    acc = b.secondary
    img.alpha_composite(logo_chip, (30, 34))
    # progress
    d.rectangle((0, 0, RW, 8), fill=(0, 0, 0, 80))
    d.rectangle((0, 0, int(RW * (idx + min(1, t / T)) / n), 8), fill=acc)
    # headline
    a = ease((t - .10) / .40)
    txt = sc.get("text", "")
    f, lines, lh = fit(d, txt, "Bold", RW - 90, 360, 84, 38, 1.12)
    y0 = 190 + (1 - a) * 60
    ov = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    y = y0
    for ln in lines:
        od.text((RW / 2 + 3, y + 4), ln, font=f, fill=(0, 0, 0, int(120 * a)), anchor="ma")
        od.text((RW / 2, y), ln, font=f, fill=(acc if idx == n - 1 else ink) + (int(255 * a),), anchor="ma")
        y += lh
    img.alpha_composite(ov)
    # sub line
    sub = sc.get("sub", "")
    if sub:
        a2 = ease((t - .55) / .4)
        fs, sl, slh = fit(d, sub, "Medium", RW - 100, 160, 38, 24, 1.25)
        ov = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        yy = y + 14 + (1 - a2) * 30
        for ln in sl:
            od.text((RW / 2, yy), ln, font=fs, fill=(255, 255, 255, int(230 * a2)), anchor="ma")
            yy += slh
        img.alpha_composite(ov)
        y = yy
    # products pop in
    if layers:
        total = sum(p.width for p in layers) + 16 * (len(layers) - 1)
        x = (RW - total) / 2
        base = RH - 150
        for k, p in enumerate(layers):
            s = max(0.01, back((t - .35 - k * .18) / .55))
            fl = 6 * math.sin(t * 2 + k)
            w, h = int(p.width * s), int(p.height * s)
            if w < 2 or h < 2:
                x += p.width + 16
                continue
            q = p.resize((w, h), Image.LANCZOS)
            sh = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
            m = q.split()[3].point(lambda v: v * 90 // 255)
            tmp = Image.new("RGBA", q.size, (0, 0, 0, 255))
            tmp.putalpha(m)
            sh.paste(tmp, (50, 62), tmp)
            from PIL import ImageFilter
            sh = sh.filter(ImageFilter.GaussianBlur(14))
            px = int(x + (p.width - w) / 2)
            py = int(base - h + fl)
            img.alpha_composite(sh, (px - 40, py - 30))
            img.alpha_composite(q, (px, py))
            x += p.width + 16
    # footer band
    d = ImageDraw.Draw(img)
    d.rectangle((0, RH - 110, RW, RH), fill=mix(b.dark, (0, 0, 0), .35))
    d.text((34, RH - 55), b.phone or b.tagline or b.name, font=font("Bold", 30, b.phone or b.tagline), fill=(255, 255, 255), anchor="lm")
    if b.handle:
        d.text((RW - 34, RH - 55), "@" + b.handle, font=font("Bold", 30), fill=acc, anchor="rm")
    # cut fade
    fa = 1 - ease(t / .18)
    if fa > 0:
        img.alpha_composite(Image.new("RGBA", (RW, RH), (0, 0, 0, int(160 * fa))))
    return img.convert("RGB")


def build_reel(b, reel, out_path, voice="none", scene_min=3.0):
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
                voice_clip(sc["say"], b, c, voice)
                d_ = max(d_, dur(c) + .5)
                clips.append((i, c))
            except Exception as ex:
                print("voice failed, reel stays silent:", str(ex)[:150], file=sys.stderr)
                clips, voice = [], "none"
        durs.append(d_)
    layers = [scene_layers(b, sc, i, n, i == n - 1) for i, sc in enumerate(scenes)]
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
    if music:
        m = random.choice(music)
        mixed = tmp / "mix.wav"
        if audio:
            run(["ffmpeg", "-v", "error", "-y", "-i", str(audio), "-stream_loop", "-1", "-i", str(m), "-filter_complex",
                 "[1:a]volume=0.12[m];[0:a][m]amix=inputs=2:duration=first:normalize=0", "-ar", "44100", str(mixed)])
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
            fr = frame(b, sc, f / FPS, durs[i], i, n, layers[i], chipimg)
            p.stdin.write(fr.tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg failed")
    return total, ("voice: " + voice if clips else "silent") + (", music" if music else "")
