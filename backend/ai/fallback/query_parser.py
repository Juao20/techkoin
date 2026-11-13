"""Rule based parser for search requests (F1 fallback).

It must stand on its own: without a Groq key this is the whole of "Recherche intelligente".
"""

from __future__ import annotations

import re
import unicodedata

from ..schemas import SearchIntent

AMOUNT_RE = re.compile(
    r"(?<![\w.,])(\d{1,3}(?:[ . ]\d{3})+|\d+(?:[.,]\d+)?)\s*"
    r"(k|mil|milles?|m|millions?|f\s?cfa|fcfa|cfa|f)?(?![\w])",
    re.I,
)
UNIT_AFTER_RE = re.compile(r"^\s*(go|gb|giga|gigas|to|tb|teras?|pouces?|%|ghz|mah|hz|mp)\b", re.I)
MAX_WORDS = ("max", "maximum", "jusqu", "moins de", "budget", "pas plus de", "<", "vers", "environ")
MIN_WORDS = ("min", "minimum", "a partir de", "plus de", "au moins", ">")

CATEGORY_WORDS = [
    ("desktop", ("pc fixe", "ordinateur fixe", "unite centrale", "desktop", "tour")),
    ("tablet", ("tablette", "ipad", "galaxy tab", "tab ")),
    (
        "laptop",
        (
            "pc portable",
            "ordinateur portable",
            "laptop",
            "macbook",
            "thinkpad",
            "pc",
            "ordi",
            "ordinateur",
        ),
    ),
    (
        "smartphone",
        (
            "telephone",
            "smartphone",
            "iphone",
            "galaxy",
            "phone",
            "mobile",
            "redmi",
            "tecno",
            "infinix",
            "itel",
            "pixel",
            "oppo",
            "huawei",
        ),
    ),
]
BRAND_ALIASES = {
    "iphone": "apple",
    "ipad": "apple",
    "macbook": "apple",
    "galaxy": "samsung",
    "thinkpad": "lenovo",
    "latitude": "dell",
    "xps": "dell",
    "elitebook": "hp",
    "probook": "hp",
    "pavilion": "hp",
    "redmi": "xiaomi",
    "spark": "tecno",
    "camon": "tecno",
    "pova": "tecno",
}
CITY_ALIASES = {"calavi": "abomey-calavi", "porto novo": "porto-novo", "portonovo": "porto-novo"}
USAGE_WORDS = [
    ("dev", ("coder", "coding", "programmer", "programmation", "developpement", "dev", "code")),
    ("gaming", ("gaming", "gamer", "jeux", "jouer", "fortnite", "fifa", "gta", "call of duty")),
    (
        "creative",
        (
            "montage",
            "video",
            "photoshop",
            "photo",
            "photos",
            "camera",
            "premiere",
            "graphisme",
            "design",
            "creation",
            "illustrator",
        ),
    ),
    ("study", ("ecole", "etude", "etudes", "etudiant", "cours", "fac", "universite", "lycee")),
    ("office", ("bureautique", "bureau", "travail", "word", "excel", "office", "secretariat")),
    (
        "battery",
        (
            "autonomie",
            "longue batterie",
            "batterie longue duree",
            "leger",
            "legere",
            "ultrabook",
            "ultra portable",
            "nomade",
        ),
    ),
    ("everyday", ("quotidien", "usage courant")),
]
# Price positioning. The words say a tier; the budget behind it comes from the live listings.
TIER_WORDS = [
    ("mid", ("milieu de gamme", "moyenne gamme", "gamme moyenne", "rapport qualite prix")),
    (
        "premium",
        (
            "premium",
            "haut de gamme",
            "luxe",
            "meilleur",
            "meilleure",
            "meilleurs",
            "performant",
            "performante",
            "puissant",
            "puissante",
            "haute performance",
            "top niveau",
        ),
    ),
    (
        "cheap",
        (
            "pas cher",
            "pas chere",
            "pas trop cher",
            "moins cher",
            "bon marche",
            "petit prix",
            "petit budget",
            "budget serre",
            "abordable",
            "economique",
            "entree de gamme",
            "premier prix",
            "low cost",
        ),
    ),
]
DESKTOP_RE = re.compile(r"\b(pc|ordinateur|ordi|ordinateurs)\s+de\s+bureau\b")
STOPWORDS = set(
    "un une des du de la le les pour pas trop cher chere vers a au aux en et ou avec sans "
    "sur dans que qui je veux voudrais cherche recherche besoin ai il y est ce cet cette mon ma "
    "mes pres proche environ max maximum moins plus budget bon bonne petit petite grand "
    "prix fcfa cfa f ultra gamer gaming premium luxe gamme meilleur meilleure meilleurs "
    "performant performante puissant puissante leger legere nomade abordable economique".split()
)


def plain(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return re.sub(r"[’']", " ", stripped)


def _to_int(number: str, suffix: str | None) -> int | None:
    raw = number.replace(" ", "").replace(" ", "")
    suffix = (suffix or "").lower().replace(" ", "")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
        raw = raw.replace(".", "")
    value = float(raw.replace(",", "."))
    if suffix in ("k", "mil", "mille", "milles"):
        value *= 1_000
    elif suffix in ("m", "million", "millions"):
        value *= 1_000_000
    elif not suffix and value < 1_000:
        return None  # a bare small number is a model, a size or a count, not a price
    return int(value)


def parse_amounts(text: str) -> tuple[int | None, int | None, list[tuple[int, int]]]:
    """Return (price_min, price_max, spans used) from phrases such as 'max 250k'."""
    spans: list[tuple[int, int]] = []
    found: list[tuple[int, int, int]] = []  # (value, start, end)
    raw: list[tuple[str, str | None, int, int]] = []
    for m in AMOUNT_RE.finditer(text):
        if UNIT_AFTER_RE.match(text[m.end() :]):
            continue
        raw.append((m.group(1), m.group(2), m.start(), m.end()))
    between = re.search(r"entre\s+\S+.*?\bet\b", text)
    if between and len(raw) >= 2 and raw[0][1] is None and raw[1][1]:
        # "entre 100 et 200k": the unit of the second amount applies to the first.
        raw[0] = (raw[0][0], raw[1][1], raw[0][2], raw[0][3])
    for number, suffix, start, end in raw:
        value = _to_int(number, suffix)
        if value is not None and value >= 1_000:
            found.append((value, start, end))
    if not found:
        return None, None, spans
    spans = [(s, e) for _, s, e in found]
    if len(found) >= 2 and between:
        low, high = sorted((found[0][0], found[1][0]))
        return low, high, spans
    value, start, _ = found[0]
    before = text[max(0, start - 22) : start]
    if any(w in before for w in MIN_WORDS) and not any(w in before for w in MAX_WORDS):
        return value, None, spans
    return None, value, spans  # "250k", "vers 250k", "max 250k": a ceiling by default


def parse(
    text: str,
    *,
    brands: list[tuple[str, str]],
    cities: list[tuple[str, str]],
    known_terms=lambda token: False,
) -> SearchIntent:
    """`brands` and `cities` are (slug, name) pairs; `known_terms(token)` says if a word names
    a device model (so it can be kept as a search term)."""
    original = text
    t = plain(text)
    intent = SearchIntent()
    hits = 0

    # Amounts first, so the numbers are not read as RAM, storage or models.
    low, high, spans = parse_amounts(t)
    intent.price_min, intent.price_max = low, high
    hits += bool(low or high)
    for s, e in sorted(spans, reverse=True):
        t = t[:s] + " " * (e - s) + t[e:]

    # « pc de bureau » is a desktop computer, not an office usage.
    desktop_phrase = bool(DESKTOP_RE.search(t))
    if desktop_phrase:
        t = DESKTOP_RE.sub("pc fixe", t)

    # Price positioning, only when no amount was given.
    if not (low or high):
        for tier, words in TIER_WORDS:
            if any(re.search(rf"\b{re.escape(w)}\b", t) for w in words):
                intent.tier = tier
                break
    hits += bool(intent.tier)

    # Brands and cities come before the category so that "iphone" can imply a smartphone.
    for slug, name in brands:
        pattern = rf"\b{re.escape(plain(name))}\b|\b{re.escape(slug)}\b"
        if re.search(pattern, t):
            intent.brands.append(slug)
    for alias, slug in BRAND_ALIASES.items():
        if re.search(rf"\b{alias}\b", t) and slug in {s for s, _ in brands} - set(intent.brands):
            intent.brands.append(slug)
    hits += bool(intent.brands)

    for alias, slug in CITY_ALIASES.items():
        if re.search(rf"\b{alias}\b", t) and slug in {s for s, _ in cities}:
            intent.city = slug
    if intent.city is None:
        for slug, name in cities:
            names = {plain(name), plain(name).replace("-", " "), slug.replace("-", " ")}
            if any(re.search(rf"\b{re.escape(n)}\b", t.replace("-", " ")) for n in names):
                intent.city = slug
                break
    hits += bool(intent.city)

    for category, words in CATEGORY_WORDS:
        if any(re.search(rf"\b{re.escape(w.strip())}\b", t) for w in words):
            intent.category = category  # later entries do not override earlier, specific ones
            break
    if intent.category == "laptop" and re.search(r"\b(fixe|tour|desktop)\b", t):
        intent.category = "desktop"
    hits += bool(intent.category)

    # Condition and grade.
    if re.search(r"comme neuf", t):
        intent.grade = ["A"]
        intent.condition = ["used", "refurbished"]
    elif re.search(r"\bneuf|neuve|scelle|sous emballage\b", t) and not re.search(r"occasion", t):
        intent.condition = ["new_sealed", "new_open"]
    elif re.search(r"occasion|seconde main|d occasion", t):
        intent.condition = ["used"]
    elif re.search(r"reconditionn|refurb", t):
        intent.condition = ["refurbished"]
    if m := re.search(r"\bgrade\s*([abc])\b", t):
        intent.grade = [m.group(1).upper()]
    hits += bool(intent.condition or intent.grade)

    # RAM and storage.
    for m in re.finditer(
        r"(\d+)\s*(go|gb|giga|gigas|to|tb|teras?)\b(\s*(?:de\s+)?(ram|memoire|ssd|stockage|disque|rom))?",
        t,
    ):
        value = int(m.group(1)) * (1024 if m.group(2) in ("to", "tb", "tera", "teras") else 1)
        tag = m.group(4)
        before = t[max(0, m.start() - 12) : m.start()]
        if tag in ("ram", "memoire"):
            intent.ram_min = value
        elif tag in ("ssd", "stockage", "disque", "rom"):
            intent.storage_min = value
        elif re.search(r"(?<!go )(ram|memoire)\s*$", before):  # "ram 16 go"
            intent.ram_min = value
        elif value >= 64:
            intent.storage_min = value
        elif value <= 32:
            intent.ram_min = value
    hits += bool(intent.ram_min or intent.storage_min)

    # Usage.
    for usage, words in USAGE_WORDS:
        if any(re.search(rf"\b{re.escape(w)}\b", t) for w in words):
            intent.usage = usage
            break
    if intent.usage in ("creative",) and intent.category in ("smartphone", "tablet"):
        intent.usage = "photo" if intent.category == "smartphone" else "creative"
    if intent.usage in ("dev", "study", "office", "creative") and intent.category == "smartphone":
        intent.usage = {"dev": "business", "study": "everyday", "office": "business"}.get(
            intent.usage, "photo"
        )
    if (
        intent.usage
        and intent.category is None
        and intent.usage in ("dev", "gaming", "creative", "study", "office")
    ):
        intent.category = "laptop"  # these needs are asked of computers far more than phones
    hits += bool(intent.usage)

    if "azerty" in t:
        intent.keyboard = "azerty"
    elif "qwerty" in t:
        intent.keyboard = "qwerty"
    hits += bool(intent.keyboard)

    # What is left and names a device model becomes a text search.
    consumed = set(intent.brands) | {"pc", "ordi", "portable", "telephone", "smartphone", "fixe"}
    leftover = re.sub(r"\d+\s*(?:go|gb|giga|gigas|to|tb|teras?)\b", " ", t)
    previous_was_model = False
    for token in re.findall(r"[a-z0-9]+", leftover):
        if token in STOPWORDS or token in consumed:
            previous_was_model = False
            continue
        if known_terms(token) and token not in intent.other_terms:
            intent.other_terms.append(token)
            previous_was_model = True
        elif token.isdigit() and previous_was_model and len(token) <= 3:
            intent.other_terms.append(token)  # "iphone 13": the number belongs to the model
            previous_was_model = False
        else:
            previous_was_model = False
    intent.other_terms = intent.other_terms[:6]
    hits += bool(intent.other_terms)

    intent.confidence = round(min(0.9, 0.25 + 0.13 * hits), 2) if hits else 0.1
    del original
    return intent
