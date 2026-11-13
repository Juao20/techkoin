"""Numbers behind the shop dashboard (spec 11: views, contacts and favorites per listing).

Everything is computed from raw events and listings, always restricted to one shop. These same
functions feed the weekly report and the chat tools, so the figures agree everywhere.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from marketplace.models import Listing

from .models import Event

CONTACT_TYPES = (Event.Type.WHATSAPP_CLICK, Event.Type.PHONE_REVEAL)
METRICS = {
    "views": (Event.Type.LISTING_VIEW,),
    "contacts": CONTACT_TYPES,
    "favorites": (Event.Type.FAVORITE_ADD,),
    "sales": (Event.Type.ORDER_PAID,),
}
PERIODS = (7, 30, 90)


def parse_period(value, default=30) -> int:
    try:
        days = int(value)
    except (TypeError, ValueError):
        return default
    return days if days in PERIODS else default


def window(days: int, ago: int = 0) -> tuple[datetime, datetime]:
    """[start, end) of the `days` days that ended `ago` periods before now."""
    end = timezone.now() - timedelta(days=days * ago)
    return end - timedelta(days=days), end


def events(shop, start, end):
    return Event.objects.filter(shop=shop, created_at__gte=start, created_at__lt=end)


def count(shop, metric: str, start, end, **extra) -> int:
    return events(shop, start, end).filter(type__in=METRICS[metric], **extra).count()


def change_pct(now: int, before: int) -> int | None:
    if before == 0:
        return None
    return round((now - before) * 100 / before)


def sold_in(shop, start, end):
    """Listings of the shop sold in the window, with their price."""
    return Listing.objects.filter(shop=shop, status="sold", sold_at__gte=start, sold_at__lt=end)


def totals(shop, days: int, ago: int = 0) -> dict:
    start, end = window(days, ago)
    sold = sold_in(shop, start, end)
    revenue = sum(sold.values_list("price_fcfa", flat=True))
    return {
        "views": count(shop, "views", start, end),
        "contacts": count(shop, "contacts", start, end),
        "favorites": count(shop, "favorites", start, end),
        "sales": sold.count(),
        "revenue_fcfa": revenue,
    }


def contact_rate(views: int, contacts: int) -> float:
    return round(contacts * 100 / views, 1) if views else 0.0


def listing_rows(shop, days: int, status=("active", "reserved")) -> list[dict]:
    """One row per listing with the period's views, contacts and favorites."""
    start, end = window(days)
    listings = list(
        Listing.objects.filter(shop=shop, status__in=status).select_related("device_model")
    )
    per = {
        row["listing"]: row
        for row in events(shop, start, end)
        .filter(listing__in=listings)
        .values("listing")
        .annotate(
            views=Count("id", filter=Q(type__in=METRICS["views"])),
            contacts=Count("id", filter=Q(type__in=METRICS["contacts"])),
            favorites=Count("id", filter=Q(type__in=METRICS["favorites"])),
        )
    }
    now = timezone.now()
    rows = []
    for listing in listings:
        stat = per.get(listing.pk, {})
        views, contacts = stat.get("views", 0), stat.get("contacts", 0)
        online_since = listing.published_at or listing.created_at
        rows.append(
            {
                "id": listing.pk,
                "slug": listing.slug,
                "title": listing.title,
                "category": listing.category,
                "status": listing.status,
                "price_fcfa": listing.price_fcfa,
                "city": listing.city,
                "days_online": max((now - online_since).days, 0),
                "views": views,
                "contacts": contacts,
                "favorites": stat.get("favorites", 0),
                "contact_rate": contact_rate(views, contacts),
            }
        )
    return rows


def daily_series(shop, days: int) -> list[dict]:
    start, end = window(days)
    rows = (
        events(shop, start, end)
        .filter(type__in=[*METRICS["views"], *CONTACT_TYPES])
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            views=Count("id", filter=Q(type__in=METRICS["views"])),
            contacts=Count("id", filter=Q(type__in=CONTACT_TYPES)),
        )
    )
    by_day = {r["day"]: r for r in rows}
    today = timezone.localdate()
    series = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        r = by_day.get(day, {})
        series.append(
            {"date": day.isoformat(), "views": r.get("views", 0), "contacts": r.get("contacts", 0)}
        )
    return series


def shop_stats(shop, days: int = 30) -> dict:
    now, before = totals(shop, days), totals(shop, days, ago=1)
    rows = listing_rows(shop, days)
    return {
        "period": days,
        "totals": {
            **now,
            "contact_rate": contact_rate(now["views"], now["contacts"]),
            "change": {k: change_pct(now[k], before[k]) for k in now},
        },
        "previous": before,
        "series": daily_series(shop, days),
        "listings": sorted(rows, key=lambda r: (-r["contacts"], -r["views"])),
        "active_listings": len(rows),
    }
