"""Market-wide reference figures the pricing and dormant-stock analyses compare a shop against."""

from __future__ import annotations

import statistics
from collections import defaultdict

from django.db.models import Count, Q

from analytics import stats
from analytics.models import Event
from marketplace.models import Listing

from .demand import SEARCH_TYPES, Resolver


def listing_activity(days: int = 30) -> dict[int, tuple[int, int]]:
    """{listing id: (views, contacts)} for every active listing of the marketplace."""
    start, end = stats.window(days)
    rows = (
        Event.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            listing__status=Listing.Status.ACTIVE,
            type__in=[*stats.METRICS["views"], *stats.CONTACT_TYPES],
        )
        .values("listing")
        .annotate(
            views=Count("id", filter=Q(type__in=stats.METRICS["views"])),
            contacts=Count("id", filter=Q(type__in=stats.CONTACT_TYPES)),
        )
    )
    return {r["listing"]: (r["views"], r["contacts"]) for r in rows}


def category_reference(days: int = 30) -> dict[str, dict]:
    """Per category: average views and contacts per active listing, and the median contact rate."""
    activity = listing_activity(days)
    by_cat: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for pk, category in Listing.objects.filter(status=Listing.Status.ACTIVE).values_list(
        "pk", "category"
    ):
        by_cat[category].append(activity.get(pk, (0, 0)))
    out = {}
    for category, items in by_cat.items():
        views = [v for v, _ in items]
        contacts = [c for _, c in items]
        rates = [c / v for v, c in items if v]
        out[category] = {
            "listings": len(items),
            "avg_views": round(sum(views) / len(items), 1),
            "avg_contacts": round(sum(contacts) / len(items), 1),
            "median_contact_rate": round(statistics.median(rates) * 100, 1) if rates else 0.0,
        }
    return out


def city_demand(days: int = 30) -> dict[str, int]:
    """Searches per city over the period (events without a city are left out)."""
    start, end = stats.window(days)
    resolver = Resolver()
    counts: dict[str, int] = defaultdict(int)
    qs = Event.objects.filter(type__in=SEARCH_TYPES, created_at__gte=start, created_at__lt=end)
    for event in qs.only("city", "filters").iterator():
        city = resolver.city_of(event)
        if city:
            counts[city] += 1
    return dict(counts)
