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
  {"kind":"mascot_hero","punch":"max 6 words, the punchline","highlight":"1-2 words copied from punch","bubble":"max 9 words, spoken by the person in the image","sticker":"max 2 words, e.g. a real product fact","cta":"short call to action","products":["product id"]},
  {"kind":"quote_poster","quote":"max 12 words, a bold quotable line","highlight":"1-3 words copied from quote","sticker":"","cta":"","products":["id"]},
  {"kind":"split_poster","problem":"max 7 words, the customer's pain","solution":"max 7 words, the brand's answer","highlight":"1-2 words copied from solution","sticker":"","cta":"","products":["id"]},
  {"kind":"comic_duo","eyebrow":"max 3 words comic caption","problem":"max 9 words, a customer line","bubble":"max 10 words, the product's punchy reply","cta":"","products":["id"]},
  {"kind":"list_cards","punch":"max 6 words","highlight":"","items":[{"title":"max 6 words"},{"title":"max 6 words"},{"title":"max 6 words"}],"sticker":"","products":["id"]}],
 "carousel":{"cover":{"punch":"max 6 words","highlight":"1-2 words from punch","products":["id"]},
   "slides":[{"title":"max 5 words","highlight":"1-2 words","body":"max 18 words","products":["id"]},{"title":"","highlight":"","body":"","products":[]},{"title":"","highlight":"","body":"","products":[]}],
   "cta":{"punch":"max 6 words","highlight":"","body":"max 14 words"}},
 "reel":{"scenes":[{"text":"max 6 words, scroll-stopping hook","highlight":"1-2 words","sub":"max 9 words","say":"one spoken sentence, 8-14 words","products":[]},{"text":"the problem, relatable","highlight":"","sub":"","say":"one spoken sentence, 8-14 words","products":[]},{"text":"meet the product","highlight":"","sub":"","say":"one spoken sentence, 8-14 words","products":["id"]},{"text":"a real benefit","highlight":"","sub":"","say":"one spoken sentence, 8-14 words","products":["id"]},{"text":"call to action","highlight":"","sub":"phone or handle line","say":"spoken call to action with the phone number or handle","products":["id"]}]},
 "captions":{"mascot_hero":"","quote_poster":"","split_poster":"","comic_duo":"","list_cards":"","carousel":"","reel":""},
 "hashtags":["6 to 8 relevant, low-competition hashtags, no #viral #fyp #explore"]
}"""

FORMULAS = {
    "pun": "a clever pun or wordplay on the product or its benefit",
    "rhyme": "two short rhyming lines",
    "myth": "bust a common myth ('Myth: ... Truth: ...' compressed to one punchy line)",
    "pov": "a relatable 'POV:' or 'Me when...' moment, short",
    "bold": "a bold confident claim, no hedging, but only using facts from the brand facts",
    "challenge": "a playful challenge or dare to the reader",
    "oneword": "a one or two word punch, then a short follow-up",
    "contrast": "'Not X. Y.' contrast structure",
}

PROMPT = """You are a sharp social-media copywriter who writes scroll-stopping, punchy, quotable lines (think short, rhythmic, witty, shareable). Write a demo content pack for the brand below, to show the brand owner what we would publish.

BRAND FACTS (JSON, the only source of truth):
{facts}

LANGUAGE / STYLE: {lang_note}
LINE STYLES: write each headline with the formula assigned to it. Every piece must sound different from the others.
{formulas}
{avoid}
RULES
- Use ONLY facts, products, offers and numbers that appear in the brand facts. Never invent prices, discounts, certificates, awards, claims or phone numbers.
- Phone number to show, if any: {phone}. Handle: @{handle}.
- The images show original illustrated people, never film/cartoon characters, celebrities or politicians; do not name any. No religious figures used for selling, no giveaways, no 'guaranteed' claims.
- Short lines hit harder: respect the word limits, no filler, no emojis in on-image text, no hashtags in captions.
- 'highlight' must be words copied exactly from the line it belongs to.
- 'products' arrays must contain only these ids: {ids}.
- Captions: 3-5 short lines, first line is a hook, end with a call to action; emojis allowed in captions.
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
    to = int(os.getenv("GEMINI_TIMEOUT") or 70)
    for m in models:
        print(f"Gemini: asking {m} ...", flush=True)
        for attempt in range(3):
            try:
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                                  headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                                  json={"contents": [{"parts": [{"text": prompt}]}],
                                        "generationConfig": {"temperature": 0.8, "responseMimeType": "application/json"}}, timeout=to)
            except Exception as ex:
                last = f"{m}: {str(ex)[:110]}"
                if "timed out" in str(ex).lower():          # slow model: go to the next one instead of waiting again
                    break
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


def fallback(b, rng=None):
    """Template copy from the brand facts (used when there is no API key). Basic, but varied."""
    import random
    rng = rng or random.Random()
    P = b.products
    ids = [p["id"] for p in P]
    p0 = P[0]
    usps = [u.rstrip(".") for u in (p0.get("usps") or [])] + ["Made for everyday use", "Easy to use", "Reliable quality"]
    u0, u1, u2 = usps[0], usps[1], usps[2]
    name, pn = b.name, p0["name"]
    tag = b.tagline or name
    cta = f"Call {b.phone}" if b.phone else ("DM @" + b.handle if b.handle else "Order now")
    heads = [f"{u0}. Done.", f"Say hello to {u0}.", f"{pn}: {u0}.", f"Not ordinary. {u0}.", f"{u0}? Sorted."]
    quotes = [f"{u0}. {u1}. That's the deal.", f"Good things come to those who choose {pn}.", f"Why settle? {u0}.", f"{u0}. Every single time."]
    probs = ["Tired of the old way?", "Still not happy with it?", "Why does this always go wrong?"]
    reply = [f"Try {pn}. {u0}.", f"{u0}. Easy.", f"Switch to {name}!"]
    rng.shuffle(heads), rng.shuffle(quotes)
    h0 = heads[0]
    hl = lambda t: " ".join(t.replace(".", "").replace("?", "").split()[:2])
    return {
        "posts": [
            {"kind": "mascot_hero", "punch": heads[0], "highlight": hl(u0), "bubble": rng.choice(reply), "sticker": u1.split()[0] if u1 else "", "cta": cta, "products": ids[:1]},
            {"kind": "quote_poster", "quote": quotes[0], "highlight": hl(u0), "sticker": "", "cta": cta, "products": ids[:1]},
            {"kind": "split_poster", "problem": rng.choice(probs), "solution": u0, "highlight": hl(u0), "sticker": "", "cta": cta, "products": ids[:1]},
            {"kind": "comic_duo", "eyebrow": "MEANWHILE...", "problem": rng.choice(probs), "bubble": rng.choice(reply), "cta": cta, "products": ids[:1]},
            {"kind": "list_cards", "punch": f"Why {name}?", "highlight": name.split()[0], "items": [{"title": u0}, {"title": u1}, {"title": u2}], "sticker": "", "products": ids[:1]}],
        "carousel": {"cover": {"punch": heads[1], "highlight": hl(u0), "products": ids[:1]},
                     "slides": [{"title": u, "highlight": hl(u), "body": "", "products": ids[:1] if i == 2 else []} for i, u in enumerate((u0, u1, u2))],
                     "cta": {"punch": "Ready when you are", "highlight": "Ready", "body": b.phone or tag}},
        "reel": {"scenes": [{"text": h0, "highlight": hl(u0), "sub": tag, "say": f"{h0} {tag}", "products": []},
                            {"text": rng.choice(probs), "highlight": "", "sub": "", "say": "Kya aap bhi yahi sochte hain?", "products": []},
                            {"text": f"Meet {pn}", "highlight": pn.split()[0], "sub": u0, "say": f"Meet {pn}. {u0}.", "products": ids[:1]},
                            {"text": u1, "highlight": hl(u1), "sub": u2, "say": f"{u1}. And {u2}.", "products": ids[:1]},
                            {"text": "Order now", "highlight": "now", "sub": b.phone or "@" + b.handle, "say": f"Order now. {b.phone}" if b.phone else "Order now. Follow us for more.", "products": ids[:1]}]},
        "captions": {k: f"{tag}\n{cta}".strip() for k in ("mascot_hero", "quote_poster", "split_poster", "comic_duo", "list_cards", "carousel", "reel")},
        "hashtags": ["#" + re.sub(r"\W", "", b.name)],
    }


def make_copy(b, use_ai=True, rng=None, avoid=None):
    import random
    rng = rng or random.Random()
    ov = b.d.get("demo_copy")
    if ov:
        return _normalise(ov, b, rng), "hand-written copy from brand.json (demo_copy)"
    key = os.getenv("GEMINI_API_KEY")
    if use_ai and key:
        models = [m for m in (os.getenv("DEMO_MODELS") or "gemini-3.7-flash,gemini-2.5-flash,gemini-3.6-flash,gemini-3.5-flash").split(",") if m]
        names = rng.sample(list(FORMULAS), 8)
        pieces = ["mascot_hero headline", "quote_poster quote", "split_poster solution", "comic_duo reply", "list_cards headline", "carousel cover", "reel hook", "carousel closing line"]
        formulas = "\n".join(f"- {pc}: {FORMULAS[n]}" for pc, n in zip(pieces, names))
        av = ("Do NOT reuse or closely copy these earlier lines:\n" + "\n".join("- " + a for a in avoid[-40:])) if avoid else ""
        prompt = PROMPT.format(facts=b.facts_text(), lang_note=LANG_NOTE.get(b.lang, b.lang), phone=b.phone or "none", handle=b.handle,
                               ids=", ".join(b.product_ids()), schema=SCHEMA, formulas=formulas, avoid=av)
        extra = b.d.get("extra_prompt")
        if extra:
            prompt += "\nEXTRA REQUIREMENTS FROM THE CLIENT: " + extra
        try:
            return _normalise(_call(prompt, models, key), b, rng), "written by Gemini from brand.json"
        except Exception as ex:
            print("AI copy failed, using template copy:", ex, file=sys.stderr)
    return fallback(b, rng), "template copy (no GEMINI_API_KEY or the AI call failed): quality is basic"


KINDS5 = ["mascot_hero", "quote_poster", "split_poster", "comic_duo", "list_cards"]


def _normalise(c, b, rng=None):
    ids = set(b.product_ids())
    fb = fallback(b, rng)
    for k in ("posts", "carousel", "reel", "captions", "hashtags"):
        c.setdefault(k, fb[k])

    def fix(lst):
        return [p for p in (lst or []) if p in ids]

    have = {p.get("kind"): p for p in c["posts"] if p.get("kind") in KINDS5}
    fbk = {p["kind"]: p for p in fb["posts"]}
    c["posts"] = [have.get(k) or fbk[k] for k in KINDS5]            # always the five families; demo.py picks 3
    for p in c["posts"]:
        p["products"] = fix(p.get("products")) or b.product_ids()[:1]
        if p["kind"] == "list_cards":
            p["items"] = [i if isinstance(i, dict) else {"title": str(i)} for i in (p.get("items") or fbk["list_cards"]["items"])][:3]
    cov = c["carousel"].setdefault("cover", fb["carousel"]["cover"])
    cov["products"] = fix(cov.get("products")) or b.product_ids()[:1]
    c["carousel"].setdefault("cta", fb["carousel"]["cta"])
    c["carousel"].setdefault("slides", fb["carousel"]["slides"])
    for s in c["carousel"]["slides"]:
        s["products"] = fix(s.get("products"))
    for s in c["reel"].get("scenes", []):
        s["products"] = fix(s.get("products"))
    c["hashtags"] = [h if h.startswith("#") else "#" + h for h in c.get("hashtags", [])][:10]
    return c


def lines_used(c):
    """Headline texts of a pack, saved to history so the next demo does not repeat them."""
    out = []
    for p in c.get("posts", []):
        for k in ("punch", "quote", "solution", "bubble", "headline"):
            if p.get(k):
                out.append(p[k])
    for k in ("punch",):
        out.append(c.get("carousel", {}).get("cover", {}).get(k, ""))
    out += [s.get("text", "") for s in c.get("reel", {}).get("scenes", [])[:1]]
    return [o for o in out if o]


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
