"""P5: the predefined functions the model may call. Each one is bound to a single shop.

The model never writes or runs SQL: it picks a function and its arguments, Django runs it on the
signed-in shop's own data, and the model words the result.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from analytics import stats
from analytics.models import Event
from marketplace.models import Listing
from marketplace.search import text_search

from . import demand, pricing_advice

METRICS = ("views", "contacts", "favorites", "sales")
CATEGORIES = ("smartphone", "tablet", "laptop", "desktop")
PERIODS = {
    "today": (0, 1),
    "7d": (0, 7),
    "30d": (0, 30),
    "90d": (0, 90),
    "this_week": (0, 7),
    "last_week": (7, 14),
    "this_month": (0, 30),
    "last_month": (30, 60),
}
PERIOD_NAMES = list(PERIODS)


class ToolError(ValueError):
    pass


def _span(name: str):
    if name not in PERIODS:
        raise ToolError(f"période inconnue : {name}")
    newer, older = PERIODS[name]
    now = timezone.now()
    return now - timedelta(days=older), now - timedelta(days=newer)


def _listings(shop, category=None, model=None):
    qs = Listing.objects.filter(shop=shop)
    if category:
        if category not in CATEGORIES:
            raise ToolError(f"catégorie inconnue : {category}")
        qs = qs.filter(category=category)
    if model:
        qs = text_search(qs, str(model))
    return qs


def _value(shop, metric: str, span, category=None, model=None) -> int:
    if metric not in METRICS:
        raise ToolError(f"mesure inconnue : {metric}")
    start, end = span
    qs = _listings(shop, category, model)
    if metric == "sales":
        return qs.filter(status="sold", sold_at__gte=start, sold_at__lt=end).count()
    return Event.objects.filter(
        listing__in=qs,
        type__in=stats.METRICS[metric],
        created_at__gte=start,
        created_at__lt=end,
    ).count()


def get_stats(shop, period: str, metric: str, category=None, model=None) -> dict:
    value = _value(shop, metric, _span(period), category, model)
    return {
        "period": period,
        "metric": metric,
        "category": category,
        "model": model,
        "value": value,
    }


def top_listings(shop, period: str, metric: str, limit: int = 5) -> dict:
    if metric not in METRICS or metric == "sales":
        raise ToolError("mesure inconnue : choisissez views, contacts ou favorites")
    start, end = _span(period)
    limit = max(1, min(int(limit or 5), 10))
    rows = []
    for listing in Listing.objects.filter(shop=shop, status__in=["active", "reserved"]):
        value = Event.objects.filter(
            listing=listing,
            type__in=stats.METRICS[metric],
            created_at__gte=start,
            created_at__lt=end,
        ).count()
        rows.append({"listing_id": listing.pk, "title": listing.title, "value": value})
    rows.sort(key=lambda r: (-r["value"], r["listing_id"]))
    return {"period": period, "metric": metric, "listings": rows[:limit]}


def compare_periods(shop, metric: str, period_a: str, period_b: str) -> dict:
    a = _value(shop, metric, _span(period_a))
    b = _value(shop, metric, _span(period_b))
    return {
        "metric": metric,
        "period_a": period_a,
        "value_a": a,
        "period_b": period_b,
        "value_b": b,
        "change_pct": stats.change_pct(a, b),
    }


def price_position(shop, listing_id=None) -> dict:
    qs = Listing.objects.filter(shop=shop, status="active")
    if listing_id:
        qs = qs.filter(pk=int(listing_id))
        if not qs.exists():
            raise ToolError("annonce introuvable dans cette boutique")
    items = []
    for listing in qs.order_by("id")[: 1 if listing_id else 8]:
        advice = pricing_advice.advise(listing)
        items.append(
            {
                "listing_id": listing.pk,
                "title": listing.title,
                "price_fcfa": listing.price_fcfa,
                "estimate_fcfa": listing.estimate_mid,
                **advice,
            }
        )
    return {"listings": items}


def demand_for(shop, model_or_family: str, city=None) -> dict:
    """Searches over 30 days for a model or family, against the supply. Small counts stay hidden."""
    label = demand.normalise_query(model_or_family)
    if not label:
        raise ToolError("précisez un modèle ou une famille")
    start, end = stats.window(30)
    resolver = demand.Resolver()
    found = demand.collect(start, end, resolver)
    wanted_city = city or None
    total = no_result = 0
    for (_, name, bound, where), seg in found.items():
        if bound is None and where == wanted_city and label in name:
            total += seg.searches
            no_result += seg.no_result
    if total < demand.MIN_SEARCHES:
        return {
            "model_or_family": label,
            "city": wanted_city,
            "too_few_searches": True,
            "note": f"Moins de {demand.MIN_SEARCHES} recherches : chiffre non communiqué.",
        }
    probe = demand.Segment("", label, None, wanted_city, terms=label)
    return {
        "model_or_family": label,
        "city": wanted_city,
        "searches_30d": total,
        "searches_without_result": no_result,
        "listings_available": demand.supply(probe),
        "my_listings": demand.supply(probe, shop),
    }


def _enum(values):
    return {"type": "string", "enum": list(values)}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stats",
            "description": "Vues, contacts, favoris ou ventes de la boutique sur une période.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": _enum(PERIOD_NAMES),
                    "metric": _enum(METRICS),
                    "category": _enum(CATEGORIES),
                    "model": {"type": "string", "description": "Mot du modèle, par exemple iphone"},
                },
                "required": ["period", "metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "top_listings",
            "description": "Annonces de la boutique avec le plus de vues, contacts ou favoris.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": _enum(PERIOD_NAMES),
                    "metric": _enum(("views", "contacts", "favorites")),
                    "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["period", "metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_periods",
            "description": "Compare une mesure entre deux périodes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": _enum(METRICS),
                    "period_a": _enum(PERIOD_NAMES),
                    "period_b": _enum(PERIOD_NAMES),
                },
                "required": ["metric", "period_a", "period_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "price_position",
            "description": "Prix d'une annonce (ou de toutes) comparé à l'estimation du marché.",
            "parameters": {
                "type": "object",
                "properties": {"listing_id": {"type": "integer"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "demand_for",
            "description": "Recherches des acheteurs pour un modèle, comparées à l'offre.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_or_family": {"type": "string"},
                    "city": {"type": "string"},
                },
                "required": ["model_or_family"],
            },
        },
    },
]


def run(shop, name: str, arguments: dict) -> dict:
    """Execute one tool call for `shop`. Unknown names and bad arguments return an error value."""
    try:
        if name == "get_stats":
            return get_stats(
                shop,
                arguments.get("period", "30d"),
                arguments.get("metric", ""),
                arguments.get("category"),
                arguments.get("model"),
            )
        if name == "top_listings":
            return top_listings(
                shop,
                arguments.get("period", "30d"),
                arguments.get("metric", "views"),
                arguments.get("limit", 5),
            )
        if name == "compare_periods":
            return compare_periods(
                shop,
                arguments.get("metric", ""),
                arguments.get("period_a", "this_week"),
                arguments.get("period_b", "last_week"),
            )
        if name == "price_position":
            return price_position(shop, arguments.get("listing_id"))
        if name == "demand_for":
            return demand_for(
                shop, str(arguments.get("model_or_family", "")), arguments.get("city")
            )
    except (ToolError, ValueError, TypeError) as exc:
        return {"error": str(exc)}
    return {"error": f"fonction inconnue : {name}"}
