"""F1: natural language search. Turns a sentence into the filters the listing search accepts."""

from __future__ import annotations

import re

from catalog.models import Brand, City, DeviceModel

from . import cache, client, privacy
from .fallback import query_parser
from .schemas import SearchIntent

USAGE_BY_FAMILY = {
    "pc": ["office", "study", "dev", "gaming", "creative", "battery"],
    "mobile": ["everyday", "photo", "gaming", "battery", "business"],
}


def _brands() -> list[tuple[str, str]]:
    return list(Brand.objects.values_list("slug", "name"))


def _cities() -> list[tuple[str, str]]:
    return list(City.objects.values_list("slug", "name"))


def _model_tokens() -> set[str]:
    tokens: set[str] = set()
    for name, aliases in DeviceModel.objects.filter(is_active=True).values_list("name", "aliases"):
        for word in re.findall(r"[a-z0-9]{3,}", query_parser.plain(name)):
            tokens.add(word)
        for alias in aliases:
            tokens.add(query_parser.plain(alias).replace(" ", ""))
    return tokens


def fallback_intent(text: str) -> SearchIntent:
    tokens = _model_tokens()
    return query_parser.parse(
        text, brands=_brands(), cities=_cities(), known_terms=lambda token: token in tokens
    )


def sanitize(intent: SearchIntent) -> SearchIntent:
    """Keep only values that exist: unknown brands and cities are dropped (spec 10.2 F1)."""
    brand_slugs = {slug for slug, _ in _brands()}
    city_slugs = {slug for slug, _ in _cities()}
    intent.brands = [b for b in intent.brands if b in brand_slugs]
    if intent.city not in city_slugs:
        intent.city = None
    if intent.price_min and intent.price_max and intent.price_min > intent.price_max:
        intent.price_min, intent.price_max = intent.price_max, intent.price_min
    intent.other_terms = [
        w for w in (query_parser.plain(t).strip() for t in intent.other_terms) if w
    ][:6]
    return intent


def to_params(intent: SearchIntent) -> dict[str, str]:
    """The query-string parameters of the search page for this intent."""
    p: dict[str, str] = {}
    if intent.category:
        p["category"] = intent.category
    if intent.brands:
        p["brand"] = ",".join(intent.brands)
    if intent.price_min:
        p["price_min"] = str(intent.price_min)
    if intent.price_max:
        p["price_max"] = str(intent.price_max)
    if intent.city:
        p["city"] = intent.city
    if intent.condition:
        p["condition"] = ",".join(intent.condition)
    if intent.grade:
        p["grade"] = ",".join(intent.grade)
    if intent.ram_min:
        p["ram_min"] = str(intent.ram_min)
    if intent.storage_min:
        p["storage_min"] = str(intent.storage_min)
    if intent.usage:
        p["usage"] = intent.usage
    if intent.keyboard:
        p["keyboard"] = intent.keyboard
    if intent.other_terms:
        p["q"] = " ".join(intent.other_terms)
    return p


CATEGORY_LABEL = {
    "smartphone": "Smartphone",
    "tablet": "Tablette",
    "laptop": "PC portable",
    "desktop": "PC fixe",
}
USAGE_LABEL = {
    "office": "bureautique",
    "study": "études",
    "dev": "développement",
    "gaming": "jeux",
    "creative": "photo et vidéo",
    "battery": "autonomie",
    "everyday": "quotidien",
    "photo": "photo",
    "business": "professionnel",
}
CONDITION_LABEL = {
    "new_sealed": "neuf scellé",
    "new_open": "neuf ouvert",
    "refurbished": "reconditionné",
    "used": "occasion",
}


def fcfa(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " FCFA"


def chips(intent: SearchIntent) -> list[dict[str, str]]:
    """The interpretation shown to the user; `keys` say which URL parameters a chip removes."""
    names = dict(_brands())
    cities = dict(_cities())
    out: list[dict] = []
    if intent.category:
        out.append({"keys": ["category"], "label": CATEGORY_LABEL[intent.category]})
    if intent.brands:
        out.append(
            {"keys": ["brand"], "label": " ou ".join(names.get(b, b) for b in intent.brands)}
        )
    if intent.price_min and intent.price_max:
        out.append(
            {
                "keys": ["price_min", "price_max"],
                "label": f"{fcfa(intent.price_min)} à {fcfa(intent.price_max)}",
            }
        )
    elif intent.price_max:
        out.append({"keys": ["price_max"], "label": f"max {fcfa(intent.price_max)}"})
    elif intent.price_min:
        out.append({"keys": ["price_min"], "label": f"dès {fcfa(intent.price_min)}"})
    if intent.city:
        out.append({"keys": ["city"], "label": cities.get(intent.city, intent.city)})
    if intent.condition:
        out.append(
            {
                "keys": ["condition"],
                "label": " ou ".join(CONDITION_LABEL[c] for c in intent.condition),
            }
        )
    if intent.grade:
        out.append({"keys": ["grade"], "label": f"état {'/'.join(intent.grade)}"})
    if intent.ram_min:
        out.append({"keys": ["ram_min"], "label": f"{intent.ram_min} Go de RAM minimum"})
    if intent.storage_min:
        out.append(
            {"keys": ["storage_min"], "label": f"{intent.storage_min} Go de stockage minimum"}
        )
    if intent.usage:
        out.append({"keys": ["usage"], "label": f"usage {USAGE_LABEL[intent.usage]}"})
    if intent.keyboard:
        out.append({"keys": ["keyboard"], "label": intent.keyboard.upper()})
    if intent.other_terms:
        out.append({"keys": ["q"], "label": " ".join(intent.other_terms)})
    return out


def run(query: str, user=None) -> dict:
    query = privacy.scrub_text(" ".join(query.split())[:200])
    key = cache.make_key("search", query.lower())
    if (hit := cache.get(key)) is not None:
        client._log("search", user, None, success=True, cache_hit=True)
        return hit

    def fallback() -> SearchIntent:
        return fallback_intent(query)

    result = client.complete(
        "search",
        "search",
        {
            "query": query,
            "categories": list(CATEGORY_LABEL),
            "brands": [{"slug": s, "name": n} for s, n in _brands()],
            "cities": [{"slug": s, "name": n} for s, n in _cities()],
            "usages": USAGE_BY_FAMILY,
        },
        SearchIntent,
        "fast",
        fallback=fallback,
        user=user,
    )
    intent = sanitize(result.value)
    payload = {
        "query": query,
        "filters": to_params(intent),
        "chips": chips(intent),
        "confidence": intent.confidence,
        "used_ai": not result.fallback_used,
    }
    cache.put(key, "search", payload)
    return payload
