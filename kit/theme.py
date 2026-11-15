"""A fresh look for every piece: mood (palette), display font, background pattern, text effect and mascot are picked at random
(different for each post, the carousel and the Reel of one demo). The brand's own colour is kept as a small accent."""
import random
from dataclasses import dataclass, field

from .common import hexrgb, mix

H = hexrgb

# bg, bg2 (pattern / gradient), accent (highlight), accent2, ink (text on bg), card, card_ink
MOODS = {
    "sunset pop":     ("#FF6B4A", "#FF9E57", "#FFE14D", "#3B1F5B", "#FFFFFF", "#FFF6E5", "#2B1B3D"),
    "neon night":     ("#12122B", "#241F5C", "#00E5FF", "#FF2E93", "#FFFFFF", "#1C1C45", "#FFFFFF"),
    "fresh mint":     ("#D8F5E3", "#A8E6C3", "#FF8A3D", "#0F5D4A", "#0F3D33", "#FFFFFF", "#0F3D33"),
    "bold primaries": ("#1D4ED8", "#3B82F6", "#FDE047", "#EF4444", "#FFFFFF", "#FFFFFF", "#101828"),
    "candy pastel":   ("#FFD6E8", "#E6D8FF", "#7C3AED", "#FF5FA8", "#3B1D5C", "#FFFFFF", "#3B1D5C"),
    "terracotta":     ("#E07A5F", "#F2A58B", "#F6E7B4", "#3D405B", "#FFFFFF", "#F4F1DE", "#3D405B"),
    "electric lime":  ("#5B21B6", "#7C3AED", "#BEF264", "#F0ABFC", "#FFFFFF", "#F5F3FF", "#2E1065"),
    "deep ocean":     ("#0C4A6E", "#0EA5E9", "#FDE68A", "#F97316", "#FFFFFF", "#ECFEFF", "#083344"),
    "royal festive":  ("#6B0F1A", "#9B1C31", "#F4C95D", "#FFF1D0", "#FFF1D0", "#FFF1D0", "#4A0A12"),
    "workshop":       ("#1F2933", "#3E4C59", "#FACC15", "#F97316", "#FFFFFF", "#FFFFFF", "#1F2933"),
    "sunny day":      ("#FFD60A", "#FFC300", "#E63946", "#1D3557", "#1D3557", "#FFFFFF", "#1D3557"),
    "teal coral":     ("#0F766E", "#14B8A6", "#FB7185", "#FEF3C7", "#FFFFFF", "#FFFBEB", "#134E4A"),
}
FONTS = {"anton": "Anton-Regular.ttf", "bebas": "BebasNeue-Regular.ttf", "lilita": "LilitaOne-Regular.ttf", "bangers": "Bangers-Regular.ttf",
         "archivo": "ArchivoBlack-Regular.ttf", "luckiest": "LuckiestGuy-Regular.ttf", "bowlby": "BowlbyOne-Regular.ttf",
         "paytone": "PaytoneOne-Regular.ttf", "righteous": "Righteous-Regular.ttf", "chango": "Chango-Regular.ttf",
         "marker": "PermanentMarker-Regular.ttf", "dmserif": "DMSerifDisplay-Regular.ttf"}
UPPER_FONTS = {"anton", "bebas", "bangers", "luckiest", "archivo"}     # look best in capitals
PATTERNS = ["dots", "stripes", "sunburst", "blobs", "grid", "halftone", "waves", "confetti", "zigzag", "checker"]
EFFECTS = ["shadow3d", "outline", "sticker", "shadow3d"]
BODIES = ["bean", "round", "squircle", "drop"]
ACCS = ["cap", "hardhat", "crown", "headband", "antenna", "sprout", "party", "glasses", "none", "bow"]


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


@dataclass
class Theme:
    mood: str
    bg: tuple
    bg2: tuple
    accent: tuple
    accent2: tuple
    ink: tuple
    card: tuple
    card_ink: tuple
    dark: tuple
    font: str
    effect: str
    pattern: str
    body: str
    acc: str
    char_col: tuple
    brand: tuple
    seed: int = 0
    chars: str = "human"
    person: dict = None

    def font_path(self):
        from .common import FONTS as FD
        return FD / "display" / FONTS[self.font]

    @property
    def upper(self):
        return self.font in UPPER_FONTS


def make(mood, rng, brand_primary, font=None, pattern=None):
    bg, bg2, a1, a2, ink, card, cink = [H(x) for x in MOODS[mood]]
    if rng.random() < .5:                         # sometimes swap the two accents for even more variety
        a1, a2 = a2, a1
    if abs(lum(a1) - lum(bg)) < 45:               # keep the highlight colour readable on the background
        a1 = (255, 255, 255) if lum(bg) < 140 else (20, 20, 30)
    dark = mix(bg, (0, 0, 0), .78) if lum(bg) > 90 else (8, 8, 20)
    char_col = rng.choice([c for c in (a1, a2, card, mix(bg2, (255, 255, 255), .25)) if sum(abs(c[i] - bg[i]) for i in range(3)) > 170 and abs(lum(c) - lum(bg)) > 30] or [(255, 255, 255) if lum(bg) < 140 else (30, 30, 50)])
    from . import art as _a
    th = Theme(mood=mood, bg=bg, bg2=bg2, accent=a1, accent2=a2, ink=ink, card=card, card_ink=cink, dark=dark,
                 font=font or rng.choice(list(FONTS)), effect=rng.choice(EFFECTS), pattern=pattern or rng.choice(PATTERNS),
                 body=rng.choice(BODIES), acc=rng.choice(ACCS), char_col=char_col, brand=brand_primary)
    th.person = _a.make_person(rng, [a1, a2, card, (255, 255, 255), mix(bg2, (0, 0, 0), .35)], bg)
    return th


def plan(n, brand_primary, seed=None, avoid_moods=(), chars="human", industry=""):
    """n themes that differ from each other: different mood, pattern and display font each."""
    rng = random.Random(seed)
    moods = [m for m in MOODS if m not in avoid_moods] or list(MOODS)
    rng.shuffle(moods)
    moods = (moods + [m for m in MOODS if m not in moods])[:n]
    fonts = rng.sample(list(FONTS), n if n <= len(FONTS) else len(FONTS))
    pats = rng.sample(PATTERNS, min(n, len(PATTERNS)))
    from . import art as _a
    roles = _a.roles_for(industry)
    rng.shuffle(roles)
    out = []
    for i in range(n):
        t = make(moods[i], rng, brand_primary, fonts[i % len(fonts)], pats[i % len(pats)])
        t.seed = rng.randrange(1 << 30)
        t.chars = chars
        t.person = _a.make_person(rng, [t.accent, t.accent2, t.card, (255, 255, 255), mix(t.bg2, (0, 0, 0), .35)], t.bg, role=roles[i % len(roles)])
        out.append(t)
    return out
