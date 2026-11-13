"""F1: natural language search. Turns a sentence into the filters the listing search accepts."""

from __future__ import annotations

import re

from catalog.models import Brand, City, DeviceModel
from marketplace.models import Listing
from marketplace.search import search_listings

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


# ----------------------------------------------------------------------------- refinement
#
# The words of a request (« pas cher », « premium », « pour jouer ») are positions on a scale, not
# exact values. They are turned into budgets and rankings from the listings that really exist,
# so a request never returns nothing just because no device is perfect.

TIER_LABEL = {"cheap": "pas cher", "mid": "milieu de gamme", "premium": "premium"}
MIN_GOOD = 3  # fewer than this at the strict usage score: look at what is nearly as good


def _round(value: int, step: int = 5_000) -> int:
    return int(round(value / step) * step)


def tier_bounds(category: str | None) -> tuple[int, int] | None:
    """Lower and upper third of the prices on sale in a category (all of them without one)."""
    qs = Listing.objects.filter(status__in=[Listing.Status.ACTIVE, Listing.Status.RESERVED])
    if category:
        qs = qs.filter(category=category)
    prices = sorted(qs.values_list("price_fcfa", flat=True))
    if len(prices) < 6:
        return None
    return _round(prices[len(prices) // 3]), _round(prices[2 * len(prices) // 3])


# What is let go, in this order, when the whole request matches nothing: the budget that came
# from a wish, then the condition, the city, the memory sizes, and last the amounts typed.
RELAX_STEPS = [
    ("le budget « {tier} »", ["price_min", "price_max"], "tier"),
    ("l'état demandé", ["condition", "grade"], None),
    ("la ville", ["city"], None),
    ("la mémoire et le stockage demandés", ["ram_min", "storage_min"], None),
    ("le budget", ["price_min", "price_max"], None),
]


def relax(intent: SearchIntent, params: dict, extra: list[dict], notes: list[str]):
    """Drop constraints one by one until something is found, and say what was dropped."""
    dropped: set[str] = set()
    live = [Listing.Status.ACTIVE, Listing.Status.RESERVED]
    if not Listing.objects.filter(status__in=live).exists():
        return params, extra, dropped  # an empty marketplace: nothing to loosen towards
    for label, keys, only in RELAX_STEPS:
        if search_listings({k: v for k, v in params.items() if k != "usage"}).exists():
            break
        if only == "tier" and not (intent.tier and not (intent.price_min or intent.price_max)):
            continue
        present = [k for k in keys if k in params]
        if not present:
            continue
        for key in present:
            params.pop(key)
        dropped |= set(present)
        notes.append(
            "Aucune annonce ne correspond à toute la demande : j'ai retiré "
            + label.format(tier=TIER_LABEL.get(intent.tier or "", ""))
            + "."
        )
    extra[:] = [c for c in extra if not dropped & set(c["keys"])]
    return params, extra, dropped


def refine(intent: SearchIntent, params: dict[str, str]) -> tuple[dict, list[dict], list[str], set]:
    """Return (params, chips replacing the raw ones, notes shown to the user, dropped keys)."""
    params = dict(params)
    extra: list[dict] = []
    notes: list[str] = []

    if intent.tier and not (intent.price_min or intent.price_max):
        bounds = tier_bounds(intent.category)
        if bounds:
            low, high = bounds
            label = TIER_LABEL[intent.tier]
            if intent.tier == "cheap":
                params["price_max"], params["sort"] = str(low), "price_asc"
                extra.append(
                    {"keys": ["price_max", "sort"], "label": f"{label}, jusqu'à {fcfa(low)}"}
                )
            elif intent.tier == "mid":
                params["price_min"], params["price_max"] = str(low), str(high)
                extra.append(
                    {
                        "keys": ["price_min", "price_max"],
                        "label": f"{label}, de {fcfa(low)} à {fcfa(high)}",
                    }
                )
            else:
                params["price_min"], params["sort"] = str(high), "price_desc"
                extra.append({"keys": ["price_min", "sort"], "label": f"{label}, dès {fcfa(high)}"})

    params, extra, dropped = relax(intent, params, extra, notes)
    baseline = {k: v for k, v in params.items() if k != "usage"}
    if intent.usage and not search_listings(baseline).exists():
        # Nothing matches the rest of the request anyway: keep the plain usage filter.
        params["usage"] = intent.usage
        extra.append({"keys": ["usage"], "label": f"usage {USAGE_LABEL[intent.usage]}"})
    elif intent.usage:
        name = USAGE_LABEL[intent.usage]
        chosen = None
        for floor in (7, 5):
            trial = {**params, "usage": intent.usage}
            if floor != 7:
                trial["usage_min"] = str(floor)
            found = search_listings(trial).count()
            if found >= MIN_GOOD or (floor == 5 and found >= 1):
                chosen = (floor, trial)
                break
        if chosen:
            floor, trial = chosen
            params = {**trial, "sort": f"usage:{intent.usage}"}
            if floor == 7:
                extra.append({"keys": ["usage", "sort"], "label": f"usage {name}"})
            else:
                extra.append(
                    {"keys": ["usage", "usage_min", "sort"], "label": f"adapté à : {name}"}
                )
                notes.append(
                    f"Peu d'appareils sont notés 7 sur 10 ou plus pour {name} : "
                    f"voici ceux notés {floor} sur 10 ou plus, les mieux notés d'abord."
                )
        else:
            params.pop("usage", None)
            params["sort"] = f"usage:{intent.usage}"
            extra.append({"keys": ["sort"], "label": f"classés pour : {name}"})
            notes.append(
                f"Aucun appareil n'est noté 5 sur 10 pour {name} : "
                "voici les mieux classés pour cet usage."
            )
    return params, extra, notes, dropped


def run(query: str, user=None) -> dict:
    query = privacy.scrub_text(" ".join(query.split())[:200])
    key = cache.make_key("search:v2", query.lower())
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
    params, extra_chips, notes, dropped = refine(intent, to_params(intent))
    replaced = {"usage"} if intent.usage else set()
    if intent.tier and not (intent.price_min or intent.price_max):
        replaced |= {"price_min", "price_max"}
    raw_chips = [c for c in chips(intent) if not (replaced | dropped) & set(c["keys"])]
    payload = {
        "query": query,
        "filters": params,
        "chips": raw_chips + extra_chips,
        "notes": notes,
        "confidence": intent.confidence,
        "used_ai": not result.fallback_used,
    }
    cache.put(key, "search", payload)
    return payload
