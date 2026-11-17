"""Realistic talking presenter Reel. Gemini Omni (gemini-omni-1.1-flash) generates a vertical video of an ordinary, fictional Indian person who speaks the
Hinglish lines herself/himself (its own voice and lip movement). We keep that audio, then lay OUR graphics on top: captions, the REAL pack shot of the
product (never redrawn by the AI), logo, footer and a soft beat. If anything fails the caller falls back to the animated Reel."""
import base64
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw

from . import art
from .common import chip, font, shadow
from .reel import RW, RH, FPS, ease, back, run, dur, layout_words, word_sprite

API = "https://generativelanguage.googleapis.com/v1beta/interactions"
MODEL = os.getenv("VIDEO_MODEL") or "gemini-omni-1.1-flash"

SETTINGS = {"adhesive": "a tidy Indian home with a wooden table and a small repair kit", "paint": "a bright Indian living room with fresh painted walls",
            "default": "a clean, bright Indian home or small shop, natural daylight"}


def _setting(b):
    ind = (b.d.get("industry") or "").lower()
    for k, v in SETTINGS.items():
        if k in ind:
            return v
    if any(t in ind for t in ("adhesive", "hardware", "construction", "tool")):
        return SETTINGS["adhesive"]
    return SETTINGS["default"]


def _who(th):
    from .photo import SKIN, ROLE_TXT, STYLE_TXT
    P = th.person
    return (f"an ordinary, friendly Indian {ROLE_TXT.get(P['role'], 'person')}, {SKIN.get(tuple(P['skin']), 'wheatish')} skin tone, "
            f"{STYLE_TXT.get(P['style'], 'short hair')}, around 30 years old")


def _prompt(b, th, lines, first, lang_note):
    who, setting = _who(th), _setting(b)
    spoken = " ".join(f'"{l}"' for l in lines)
    base = (f"Vertical smartphone video of {who} in {setting}, speaking straight to the camera like an Instagram creator, natural handheld framing from chest up, "
            f"real skin texture, natural gestures and expressions, lip-synced. The person says, in {lang_note}, in a warm, upbeat, conversational voice: {spoken} "
            "No on-screen text, no subtitles, no logos, no brand names or readable packaging in the shot. No music. This is a fictional person who does not resemble any real or famous individual.")
    return base if first else f"The same person, same place, same voice, continues the video and says: {spoken} Keep it natural and continuous. No on-screen text, no music."


def _post(body, key):
    r = requests.post(API, headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=body, timeout=int(os.getenv("VIDEO_TIMEOUT") or 420))
    if not r.ok:
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    return r.json()


def _extract(j, key, out):
    """pull the video from an interaction reply (inline base64 or hosted uri) and save it"""
    for st in j.get("steps", []):
        for c in st.get("content", []) or []:
            if c.get("type") == "video":
                if c.get("data"):
                    Path(out).write_bytes(base64.b64decode(c["data"]))
                    return
                if c.get("uri"):
                    fid = c["uri"].rstrip("/").split("/")[-1].split(":")[0]
                    for _ in range(60):
                        s = requests.get(f"https://generativelanguage.googleapis.com/v1beta/files/{fid}", headers={"x-goog-api-key": key}, timeout=60).json()
                        if s.get("state") == "ACTIVE":
                            break
                        if s.get("state") == "FAILED":
                            raise RuntimeError("video file failed")
                        time.sleep(5)
                    d = requests.get(f"https://generativelanguage.googleapis.com/v1beta/files/{fid}:download?alt=media", headers={"x-goog-api-key": key}, timeout=300)
                    d.raise_for_status()
                    Path(out).write_bytes(d.content)
                    return
    raise RuntimeError("no video in reply")


def generate(b, th, scenes, work):
    """Returns the path of one continuous talking video (first call + up to 2 extensions, same person and voice)."""
    key = os.environ["GEMINI_API_KEY"]
    from .voice import STYLE
    note = {"hinglish": "natural Hinglish (Hindi and English mixed)", "hindi": "natural Hindi", "english": "natural Indian English", "marathi": "natural Marathi", "bengali": "natural Bengali"}.get(b.lang, "natural Hinglish")
    says = [s.get("say") for s in scenes if s.get("say")]
    groups = [says[0:2], says[2:4], says[4:5]]
    groups = [g for g in groups if g]
    fmt = {"type": "video", "aspect_ratio": "9:16", "resolution": os.getenv("VIDEO_RES") or "720p", "delivery": "uri"}
    j = _post({"model": MODEL, "input": _prompt(b, th, groups[0], True, note), "response_format": fmt}, key)
    cur = Path(work) / "p0.mp4"
    _extract(j, key, cur)
    last_id = j.get("id")
    for k, g in enumerate(groups[1:], 1):
        nxt = Path(work) / f"p{k}.mp4"
        try:
            j2 = _post({"model": MODEL, "input": _prompt(b, th, g, False, note), "previous_interaction_id": last_id,
                        "generation_config": {"video_config": {"task": "extend"}}, "response_format": fmt}, key)
            _extract(j2, key, nxt)
        except Exception as ex:
            print("presenter: extension failed, using what we have:", str(ex)[:160], file=sys.stderr)
            break
        # the reply is either the whole extended video or only the new part: join if it is only the new part
        if dur(nxt) > dur(cur) + 1.5:
            cur = nxt
        else:
            lst = Path(work) / f"j{k}.txt"
            lst.write_text(f"file '{cur}'\nfile '{nxt}'\n")
            joined = Path(work) / f"joined{k}.mp4"
            run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", f"scale={RW}:{RH}:force_original_aspect_ratio=increase,crop={RW}:{RH},fps={FPS}",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-ar", "44100", str(joined)])
            cur = joined
        last_id = j2.get("id") or last_id
    return cur


def _overlay_plan(scenes, total):
    w = [max(8, len(s.get("say") or s.get("text") or "")) for s in scenes]
    cum, t = [], 0.0
    for x in w:
        cum.append((t, t + total * x / sum(w)))
        t += total * x / sum(w)
    return cum


def compose(b, th, scenes, src, out_path, music=True):
    total = dur(src)
    plan = _overlay_plan(scenes, total)
    chipimg = Image.new("RGBA", (RW, 160), (0, 0, 0, 0))
    chip(chipimg, b, x=0, y=0, w=150)
    chipimg = chipimg.crop((0, 0, 190, 100))
    sc = []
    for i, s in enumerate(scenes):
        has_p = bool(s.get("products"))
        words, ybot = layout_words(th, s.get("text", ""), s.get("highlight", ""), (30, 790, (RW - 310) if has_p else (RW - 30), 1030), start=92, min_size=40)
        spr = [(w, *word_sprite(th, w, f, col, size), x, y, size) for (w, f, x, y, col, size) in words]
        pr = None
        if s.get("products"):
            p = b.product(s["products"][0])
            h = 330
            pr = p.resize((int(p.width * h / p.height), h), Image.LANCZOS)
            if pr.width > 280:
                pr = pr.resize((280, int(pr.height * 280 / pr.width)), Image.LANCZOS)
        sc.append((spr, pr))
    tmp = Path(tempfile.mkdtemp(prefix="pres_"))
    silent = tmp / "silent.mp4"
    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), "-vf", f"scale={RW}:{RH}:force_original_aspect_ratio=increase,crop={RW}:{RH},fps={FPS}",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    fsz = RW * RH * 3
    n = 0
    while True:
        buf = rd.stdout.read(fsz)
        if len(buf) < fsz:
            break
        t = n / FPS
        n += 1
        im = Image.frombytes("RGB", (RW, RH), buf).convert("RGBA")
        i = next((k for k, (a, z) in enumerate(plan) if a <= t < z), len(plan) - 1)
        a0 = plan[i][0]
        lt = t - a0
        # soft dark gradient so captions stay readable on any footage
        g = Image.new("RGBA", (RW, 520), (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        for y in range(520):
            gd.line((0, y, RW, y), fill=(0, 0, 0, int(190 * (y / 520) ** 1.6)))
        im.alpha_composite(g, (0, RH - 520))
        im.alpha_composite(chipimg, (30, 34))
        spr, pr = sc[i]
        for k, (w, L, pad, x, y, size) in enumerate(spr):
            s_ = back((lt - .05 - k * .12) / .3)
            if s_ <= .02:
                continue
            q = L.resize((max(1, int(L.width * s_)), max(1, int(L.height * s_))), Image.LANCZOS)
            im.alpha_composite(q, (int(x - pad + L.width / 2 - q.width / 2), int(y - pad + L.height / 2 - q.height / 2)))
        if pr is not None:
            a = back((lt - .3) / .5)
            if a > .02:
                q = pr.resize((max(1, int(pr.width * a)), max(1, int(pr.height * a))), Image.LANCZOS)
                px, py = RW - q.width - 30, int(RH - 130 - q.height - 20 + 6 * __import__("math").sin(t * 3))
                shadow(im, q, (px, py), blur=14, off=(8, 14), a=110)
                im.alpha_composite(q, (px, py))
        d = ImageDraw.Draw(im)
        d.rectangle((0, RH - 100, RW, RH), fill=th.dark)
        d.rectangle((0, RH - 100, RW, RH - 94), fill=b.primary)
        d.text((34, RH - 46), b.phone or b.tagline or b.name, font=font("Bold", 30, b.phone or b.tagline), fill=(255, 255, 255), anchor="lm")
        if b.handle:
            d.text((RW - 34, RH - 46), "@" + b.handle, font=font("Bold", 30), fill=(255, 255, 255), anchor="rm")
        d.rectangle((0, 0, int(RW * min(1, t / total)), 8), fill=th.accent)
        wr.stdin.write(im.convert("RGB").tobytes())
    wr.stdin.close()
    wr.wait()
    rd.wait()
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(src)]
    if music and os.getenv("REEL_MUSIC", "on") != "off":
        from . import music as M
        beat = tmp / "beat.wav"
        M.track(total + 1, th.seed, beat)
        cmd += ["-i", str(beat), "-filter_complex", "[1:a]volume=1.0[v];[2:a]volume=0.07[m];[v][m]amix=inputs=2:duration=first:normalize=0[a]", "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out_path)]
    run(cmd)
    return total


def build(b, th, reel, out_path):
    work = Path(tempfile.mkdtemp(prefix="presgen_"))
    src = generate(b, th, reel["scenes"], work)
    total = compose(b, th, reel["scenes"], src, out_path)
    return total, "realistic AI presenter (speaks by itself), real pack shot overlaid"
