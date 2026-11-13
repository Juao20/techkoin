"""P1, « Radar de la demande »: what buyers search for compared with what is on sale.

Searches (`search` and `search_no_result` events) of the last 7 or 30 days are grouped by
(category, model or family, budget bracket, city), then set against the active listings that the
real search would return for the same words. A segment is shown only when it gathers at least
10 searches (privacy threshold of spec 10.3). When a city is too thin on its own, its searches
still count in the all-cities row of the same family.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

from django.utils.text import slugify

from analytics import stats
from analytics.models import Event
from catalog.models import City
from catalog.search import find_models
from marketplace.models import Listing
from marketplace.search import text_search

from . import llm
from .schemas import DemandAdvice

MIN_SEARCHES = 10  # a segment below this is never shown
BUDGET_STEPS = (100_000, 200_000, 400_000, 700_000)

SEARCH_TYPES = (Event.Type.SEARCH, Event.Type.SEARCH_NO_RESULT)


CATEGORY_NAME = {
    "smartphone": "Smartphones",
    "tablet": "Tablettes",
    "laptop": "PC portables",
    "desktop": "PC fixes",
}


@dataclass
class Segment:
    """`terms` are the words typed (matched like the real search); a search made only with
    filters has no terms and is described by its category and brand instead."""

    category: str
    label: str
    budget_max: int | None
    city: str | None
    terms: str = ""
    brand: str = ""
    searches: int = 0
    no_result: int = 0
    budgets: list[int] = field(default_factory=list)


def budget_bracket(price_max) -> int | None:
    """Upper bound of the bracket a « price_max » filter falls in (None: no budget given)."""
    try:
        value = int(price_max)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return next((step for step in BUDGET_STEPS if value <= step), 10**9)


def budget_label(bound: int | None) -> str:
    if bound is None:
        return ""
    if bound >= 10**9:
        return f"plus de {BUDGET_STEPS[-1]:,}".replace(",", " ") + " FCFA"
    return f"moins de {bound:,}".replace(",", " ") + " FCFA"


def normalise_query(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


class Resolver:
    """Turns an event into its (category, label, city) once, remembering repeated queries."""

    def __init__(self):
        self.cities = {c.slug: c.name for c in City.objects.all()}
        self.queries: dict[str, str] = {}

    def category_of(self, query: str) -> str:
        if query not in self.queries:
            found = find_models(query, limit=1) if query else []
            self.queries[query] = found[0].category if found else ""
        return self.queries[query]

    def city_of(self, event) -> str | None:
        raw = event.city or (event.filters or {}).get("city") or ""
        slug = slugify(raw)
        return self.cities.get(slug) or (raw if raw in self.cities.values() else None)

    def segment_key(self, event) -> tuple | None:
        filters = event.filters or {}
        query = normalise_query(event.query_text or filters.get("q", ""))
        category = str(filters.get("category") or "").split(",")[0]
        brand = str(filters.get("brand") or "").split(",")[0]
        if query:
            category = category or self.category_of(query)
        elif not (category or brand):
            return None
        bound, city = budget_bracket(filters.get("price_max")), self.city_of(event)
        return category, query, brand, bound, city


def collect(start, end, resolver: Resolver) -> dict[tuple, Segment]:
    """Count the searches of a window under every key, including the all-cities rollup."""
    found: dict[tuple, Segment] = {}
    qs = Event.objects.filter(type__in=SEARCH_TYPES, created_at__gte=start, created_at__lt=end)
    for event in qs.only("type", "query_text", "filters", "city").iterator():
        key = resolver.segment_key(event)
        if key is None:
            continue
        category, terms, brand, bound, city = key
        label = terms or " ".join(
            p
            for p in (CATEGORY_NAME.get(category, "Appareils"), brand.replace("-", " ").title())
            if p
        )
        price_max = (event.filters or {}).get("price_max")
        for scope in {city, None}:  # the city row and the all-cities row
            full = (category, label, bound, scope)
            seg = found.setdefault(
                full, Segment(category, label, bound, scope, terms=terms, brand=brand)
            )
            seg.searches += 1
            seg.no_result += event.type == Event.Type.SEARCH_NO_RESULT
            if price_max and str(price_max).isdigit():
                seg.budgets.append(int(price_max))
    return found


def supply(seg: Segment, shop=None) -> int:
    qs = Listing.objects.filter(status=Listing.Status.ACTIVE)
    if shop is not None:
        qs = qs.filter(shop=shop)
    if seg.category:
        qs = qs.filter(category=seg.category)
    if seg.city:
        qs = qs.filter(city__iexact=seg.city)
    if seg.budget_max is not None and seg.budget_max < 10**9:
        qs = qs.filter(price_fcfa__lte=seg.budget_max)
    elif seg.budget_max is not None:
        qs = qs.filter(price_fcfa__gt=BUDGET_STEPS[-1])
    if seg.brand:
        qs = qs.filter(brand__slug=seg.brand)
    return text_search(qs, seg.terms).count() if seg.terms else qs.count()


def radar(shop, days: int = 7) -> dict:
    """Segments ranked « strong demand, weak supply », with the previous period for trend."""
    resolver = Resolver()
    now_start, now_end = stats.window(days)
    before_start, before_end = stats.window(days, ago=1)
    current = collect(now_start, now_end, resolver)
    previous = collect(before_start, before_end, resolver)
    rows = []
    for key, seg in current.items():
        if seg.searches < MIN_SEARCHES:
            continue
        available = supply(seg)
        before = previous.get(key)
        rows.append(
            {
                "category": seg.category,
                "label": seg.label,
                "budget_max": None if seg.budget_max is None else min(seg.budget_max, 10**9),
                "budget_label": budget_label(seg.budget_max),
                "city": seg.city,
                "searches": seg.searches,
                "no_result": seg.no_result,
                "supply": available,
                "my_supply": supply(seg, shop),
                "median_budget_fcfa": (
                    int(statistics.median(seg.budgets)) if len(seg.budgets) >= 3 else None
                ),
                "previous_searches": before.searches if before else 0,
                "change_pct": stats.change_pct(seg.searches, before.searches if before else 0),
                "searches_per_listing": round(seg.searches / max(available, 1), 1),
            }
        )
    # When every search of a family came from one city, the all-cities row only repeats it.
    city_totals = {
        (r["category"], r["label"], r["budget_max"]): r["searches"] for r in rows if r["city"]
    }
    rows = [
        r
        for r in rows
        if r["city"]
        or city_totals.get((r["category"], r["label"], r["budget_max"])) != r["searches"]
    ]
    rows.sort(key=lambda r: (-r["searches_per_listing"], -r["searches"], r["label"]))
    return {"period": days, "min_searches": MIN_SEARCHES, "rows": rows}


def describe_row(row: dict) -> str:
    """« 87 recherches pour « macbook m1 » à moins de 400 000 FCFA à Cotonou, 3 annonces. »"""
    where = f" à {row['city']}" if row["city"] else ""
    budget = f" {row['budget_label']}" if row["budget_label"] else ""
    return (
        f"{row['searches']} recherches pour « {row['label']} »{budget}{where}, "
        f"{row['supply']} annonce(s) disponible(s)"
    )


def recommendations(shop, rows: list[dict]) -> tuple[list[str], bool]:
    """Up to 3 purchase recommendations worded by the model from the table (spec P1)."""
    top = [r for r in rows if r["searches_per_listing"] >= 2][:6]
    if not top:
        return [
            "La demande observée est couverte par l'offre actuelle : rien à acheter en priorité."
        ], False

    def fallback() -> DemandAdvice:
        lines = [
            f"{describe_row(r)} : "
            + (
                "beaucoup de ces recherches restent sans résultat, c'est une demande à servir."
                if r["no_result"] * 2 >= r["searches"]
                else "l'offre est faible, c'est une demande à servir."
            )
            for r in top[:3]
        ]
        return DemandAdvice(recommendations=lines)

    data = [
        {
            k: r[k]
            for k in (
                "label",
                "budget_label",
                "city",
                "searches",
                "supply",
                "my_supply",
                "no_result",
                "change_pct",
            )
        }
        for r in top
    ]
    value, used_ai = llm.write(
        "insights_demand",
        "insights_demand",
        data,
        DemandAdvice,
        fallback,
        lambda v: v.recommendations,
        shop=shop,
    )
    return value.recommendations, used_ai
