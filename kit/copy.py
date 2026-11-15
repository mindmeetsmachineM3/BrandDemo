"""Demo copy: written by Gemini from brand.json (needs GEMINI_API_KEY), with a template fallback and a hand-written override."""
import json
import os
import re
import sys
import time

BANNED = ["disney", "doraemon", "tom and jerry", "tom & jerry", "mickey", "marvel", "bollywood", "shah rukh", "salman", "amitabh", "modi",
          "rahul gandhi", "kohli", "dhoni", "cartoon", "celebrity", "god ", "bhagwan", "free trip", "lottery", "guaranteed returns"]
WARN_WORDS = ["guarantee", "100%", "no.1", "#1", "best in", "cheapest", "lifetime", "certified", "approved by"]

SCHEMA = """{
 "posts":[
  {"kind":"hero","eyebrow":"3-4 words","headline":"max 6 words","highlight":"max 4 words","body":"max 22 words","cta":"short call to action","badge":"","products":["product id"]},
  {"kind":"offer","eyebrow":"","headline":"max 6 words","highlight":"","body":"max 16 words","cta":"","badge":"short offer text from the brand facts, or empty","products":["id","id"]},
  {"kind":"tips","eyebrow":"","headline":"max 5 words","highlight":"max 3 words","items":[{"title":"max 4 words","body":"max 10 words"},{"title":"","body":""},{"title":"","body":""}],"note":"short note","products":["id"]}],
 "carousel":{"cover":{"eyebrow":"","headline":"max 6 words","highlight":"max 4 words","products":["id"]},
   "slides":[{"title":"max 5 words","body":"max 22 words","products":["id"]},{"title":"","body":"","products":[]},{"title":"","body":"","products":[]}],
   "cta":{"headline":"max 6 words","body":"max 16 words"}},
 "reel":{"scenes":[{"text":"max 6 words, hook","sub":"max 10 words","say":"one spoken sentence, 8-14 words","products":[]},{"text":"","sub":"","say":"","products":[]},{"text":"","sub":"","say":"","products":[]},{"text":"","sub":"","say":"","products":["id"]},{"text":"call to action","sub":"phone or handle line","say":"","products":["id"]}]},
 "captions":{"post_1":"","post_2":"","post_3":"","carousel":"","reel":""},
 "hashtags":["6 to 8 relevant, low-competition hashtags, no #viral #fyp #explore"]
}"""

PROMPT = """You are a senior social-media copywriter. Write a demo content pack for the brand below, to show the brand owner what we would publish.

BRAND FACTS (JSON, the only source of truth):
{facts}

LANGUAGE / STYLE: {lang_note}
RULES
- Use ONLY facts, products, offers and numbers that appear in the brand facts. Never invent prices, discounts, certificates, awards, claims or phone numbers.
- Phone number to show, if any: {phone}. Handle: @{handle}.
- No cartoon or film characters, no celebrities or politicians, no religious figures used for selling, no giveaways, no 'guaranteed' claims.
- Every product post must show a real use and a real benefit from the facts. Short punchy headlines, no emojis in headlines.
- 'products' arrays must contain only these ids: {ids}.
- Captions: 3-5 short lines, first line is a hook, end with a call to action; emojis allowed in captions; no hashtags inside captions.
- Obey the brand's own do/dont lists and extra requirements.
Return ONLY JSON in exactly this shape:
{schema}"""

LANG_NOTE = {
    "english": "simple Indian English",
    "hinglish": "Hinglish: Hindi written in Latin letters mixed with simple English, like everyday Indian speech",
    "hindi": "simple Hindi in Devanagari",
    "marathi": "simple spoken Marathi in Devanagari",
    "bengali": "simple Bengali in Bengali script",
}


def _call(prompt, models, key):
    import requests
    last = ""
    for m in models:
        for attempt in range(3):
            try:
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                                  headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                                  json={"contents": [{"parts": [{"text": prompt}]}],
                                        "generationConfig": {"temperature": 0.8, "responseMimeType": "application/json"}}, timeout=120)
            except Exception as ex:
                last = str(ex)[:150]
                time.sleep(4)
                continue
            if r.ok:
                try:
                    txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip())
                except Exception as ex:
                    last = f"{m}: bad JSON ({ex})"
                    continue
            last = f"{m}: {r.status_code} {r.text[:120]}"
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(8 * (attempt + 1))
                continue
            break
        print("Gemini:", last, file=sys.stderr)
    raise RuntimeError(last)


def fallback(b):
    """Plain template copy from the brand facts (used when there is no API key)."""
    P = b.products
    ids = [p["id"] for p in P]
    p0 = P[0]
    usps = (p0.get("usps") or ["Made for everyday use", "Easy to use", "Reliable quality"]) + ["Easy to use", "Reliable quality"]
    offer = (b.d.get("offers") or [""])[0]
    tag = b.tagline or b.name
    items = [{"title": u.rstrip("."), "body": ""} for u in usps[:3]]
    return {
        "posts": [
            {"kind": "hero", "eyebrow": (b.d.get("industry") or b.name).upper(), "headline": p0["name"], "highlight": usps[0].rstrip("."),
             "body": p0.get("description", usps[1]), "cta": b.phone and f"Call / WhatsApp: {b.phone}" or "", "badge": "", "products": ids[:2]},
            {"kind": "offer", "eyebrow": "", "headline": offer or f"Meet {b.name}", "highlight": "", "body": tag, "cta": b.phone, "badge": "", "products": ids[:3]},
            {"kind": "tips", "eyebrow": "WHY " + b.name.upper(), "headline": f"3 reasons to choose {p0['name']}", "highlight": "", "items": items,
             "note": "", "products": ids[:1]}],
        "carousel": {"cover": {"eyebrow": b.name.upper(), "headline": p0["name"], "highlight": usps[0].rstrip("."), "products": ids[:2]},
                     "slides": [{"title": u.rstrip("."), "body": "", "products": ids[:1]} for u in usps[:3]],
                     "cta": {"headline": "Get in touch", "body": b.phone or tag}},
        "reel": {"scenes": [{"text": p0["name"], "sub": tag, "say": "", "products": ids[:1]},
                            {"text": usps[0].rstrip("."), "sub": "", "say": "", "products": []},
                            {"text": usps[1].rstrip("."), "sub": "", "say": "", "products": []},
                            {"text": usps[2].rstrip("."), "sub": "", "say": "", "products": ids[:2]},
                            {"text": "Order now", "sub": b.phone or "@" + b.handle, "say": "", "products": ids[:2]}]},
        "captions": {k: f"{tag}\n{b.phone}".strip() for k in ("post_1", "post_2", "post_3", "carousel", "reel")},
        "hashtags": ["#" + re.sub(r"\W", "", b.name)],
    }


def make_copy(b, use_ai=True, character="realistic"):
    ov = b.d.get("demo_copy")
    if ov:
        return ov, "hand-written copy from brand.json (demo_copy)"
    key = os.getenv("GEMINI_API_KEY")
    if use_ai and key:
        models = [m for m in (os.getenv("DEMO_MODELS") or "gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash,gemini-2.5-flash").split(",") if m]
        prompt = PROMPT.format(facts=b.facts_text(), lang_note=LANG_NOTE.get(b.lang, b.lang), phone=b.phone or "none", handle=b.handle,
                               ids=", ".join(b.product_ids()), schema=SCHEMA)
        extra = b.d.get("extra_prompt")
        if extra:
            prompt += "\nEXTRA REQUIREMENTS FROM THE CLIENT: " + extra
        try:
            return _normalise(_call(prompt, models, key), b), "written by Gemini from brand.json"
        except Exception as ex:
            print("AI copy failed, using template copy:", ex, file=sys.stderr)
    return fallback(b), "template copy (no GEMINI_API_KEY or the AI call failed): quality is basic"


def _normalise(c, b):
    ids = set(b.product_ids())
    fb = fallback(b)
    for k in ("posts", "carousel", "reel", "captions", "hashtags"):
        c.setdefault(k, fb[k])

    def fix(lst):
        return [p for p in (lst or []) if p in ids]

    for p in c["posts"]:
        p["products"] = fix(p.get("products")) or b.product_ids()[:2]
    while len(c["posts"]) < 3:
        c["posts"].append(fb["posts"][len(c["posts"])])
    c["carousel"]["cover"]["products"] = fix(c["carousel"]["cover"].get("products")) or b.product_ids()[:2]
    for s in c["carousel"].get("slides", []):
        s["products"] = fix(s.get("products"))
    for s in c["reel"].get("scenes", []):
        s["products"] = fix(s.get("products"))
    c["hashtags"] = [h if h.startswith("#") else "#" + h for h in c.get("hashtags", [])][:10]
    return c


def checks(c, b):
    """Return a list of warnings the human must look at before sending the demo."""
    txt = json.dumps(c, ensure_ascii=False).lower()
    out = []
    for w in BANNED:
        if w in txt:
            out.append(f"BLOCK: banned word '{w}' found. Rewrite before sending.")
    for w in WARN_WORDS:
        if w in txt:
            out.append(f"CHECK: claim word '{w}' used. Confirm it with the client.")
    facts = b.facts_text().lower()
    for num in set(re.findall(r"\d[\d,\.]*", txt)):
        n = num.strip(".,")
        if len(n) >= 2 and n not in facts:
            out.append(f"CHECK: number '{n}' is not in brand.json. Confirm it.")
    for ph in set(re.findall(r"\+?\d[\d ]{8,}\d", json.dumps(c, ensure_ascii=False))):
        if b.phone and re.sub(r"\D", "", ph)[-10:] != re.sub(r"\D", "", b.phone)[-10:]:
            out.append(f"BLOCK: phone number '{ph}' differs from brand.json.")
    return out
