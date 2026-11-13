"""P3, « Diagnostic du stock dormant ».

A listing is dormant when it has been online for more than 14 days and converts views to contacts
below the median of its category. Causes are found by rules; the model words the explanation;
the corrections are the F2 text (checked against the listing's own facts) and the P2 price.
"""

from __future__ import annotations

import statistics
from datetime import timedelta

from django.utils import timezone

from ai import cache, describe
from marketplace.models import Listing

from . import llm, market, pricing_advice
from .schemas import ListingNotes

MIN_DAYS = 14
MIN_PHOTOS = 6
MIN_WORDS = 40
FIX_LIMIT = 5  # listings that get a ready-made correction per request (each costs a model call)
FIX_TTL = timedelta(hours=24)

REQUIRED_SPECS = {
    "laptop": ("ram_gb", "storage_gb", "processor_id"),
    "desktop": ("ram_gb", "storage_gb", "processor_id"),
    "smartphone": ("storage_gb", "battery_health_pct", "ram_gb"),
    "tablet": ("storage_gb", "battery_health_pct"),
}
SPEC_LABEL = {
    "ram_gb": "mémoire vive",
    "storage_gb": "stockage",
    "processor_id": "processeur",
    "battery_health_pct": "santé de la batterie",
}


def causes_for(listing: Listing, advice: dict, photos: int, city_counts: dict[str, int]) -> list:
    causes = []
    if advice["action"] == "lower":
        causes.append(
            {
                "code": "price_above_market",
                "label": "Prix au-dessus du marché",
                "detail": f"{advice['gap_pct']} % au-dessus de l'estimation",
            }
        )
    if photos < MIN_PHOTOS:
        causes.append(
            {
                "code": "few_photos",
                "label": "Peu de photos",
                "detail": f"{photos} photo(s) sur {MIN_PHOTOS} conseillées",
            }
        )
    words = len((listing.description or "").split())
    if words < MIN_WORDS:
        causes.append(
            {
                "code": "short_description",
                "label": "Description trop courte",
                "detail": f"{words} mots, au moins {MIN_WORDS} conseillés",
            }
        )
    missing = [
        SPEC_LABEL[f]
        for f in REQUIRED_SPECS.get(listing.category, ())
        if getattr(listing, f) in (None, "")
    ]
    if missing:
        causes.append(
            {
                "code": "missing_specs",
                "label": "Caractéristiques manquantes",
                "detail": ", ".join(missing),
            }
        )
    if city_counts and listing.city:
        typical = statistics.median(city_counts.values())
        if city_counts.get(listing.city, 0) < typical * 0.5:
            causes.append(
                {
                    "code": "low_demand_city",
                    "label": "Ville peu demandée",
                    "detail": f"{listing.city} : peu de recherches comparé aux autres villes",
                }
            )
    return causes


def _fallback_note(row: dict) -> str:
    first = row["causes"][0]
    return (
        f"{first['label']} ({first['detail']}). "
        f"Corrigez cela en premier : {len(row['causes'])} point(s) à revoir sur cette annonce."
    )


def correction(listing: Listing, shop) -> dict:
    """Ready-to-apply title and description (F2), cached per listing version."""
    key = cache.make_key("dormant-fix", {"id": listing.pk, "v": listing.updated_at.isoformat()})
    if (hit := cache.get(key)) is not None:
        return hit
    text = describe.run(listing, user=shop.owner)
    fix = {"title": text["title"], "description": text["description"], "used_ai": text["used_ai"]}
    cache.put(key, "dormant-fix", fix, FIX_TTL)
    return fix


def diagnose(shop, days: int = 30, with_fixes: bool = True, use_model: bool = True) -> dict:
    activity = market.listing_activity(days)
    reference = market.category_reference(days)
    cities = market.city_demand(days)
    now = timezone.now()
    cutoff = now - timedelta(days=MIN_DAYS)
    rows = []
    qs = (
        Listing.objects.filter(shop=shop, status=Listing.Status.ACTIVE)
        .select_related("processor")
        .prefetch_related("photos")
    )
    for listing in qs:
        online_since = listing.published_at or listing.created_at
        if online_since > cutoff:
            continue
        views, contacts = activity.get(listing.pk, (0, 0))
        rate = round(contacts * 100 / views, 1) if views else 0.0
        median = reference.get(listing.category, {}).get("median_contact_rate", 0.0)
        if rate >= median:
            continue
        advice = pricing_advice.advise(listing)
        causes = causes_for(listing, advice, len(listing.photos.all()), cities)
        rows.append(
            {
                "id": listing.pk,
                "slug": listing.slug,
                "title": listing.title,
                "price_fcfa": listing.price_fcfa,
                "days_online": (now - online_since).days,
                "views": views,
                "contacts": contacts,
                "contact_rate": rate,
                "median_contact_rate": median,
                "causes": causes,
                "advised_price_fcfa": (
                    advice["advised_price_fcfa"] if advice["action"] == "lower" else None
                ),
                "listing": listing,
            }
        )
    rows.sort(key=lambda r: (-len(r["causes"]), -r["days_online"], r["id"]))

    used_ai = False
    with_causes = [r for r in rows if r["causes"]]
    if with_causes and use_model:
        data = [
            {k: r[k] for k in ("id", "title", "days_online", "views", "contacts", "causes")}
            for r in with_causes[:10]
        ]
        ids = {r["id"] for r in with_causes[:10]}

        def fallback() -> ListingNotes:
            return ListingNotes(
                items=[{"listing_id": r["id"], "note": _fallback_note(r)} for r in with_causes[:10]]
            )

        def check(value: ListingNotes) -> None:
            if {n.listing_id for n in value.items} != ids:
                raise ValueError("annonces manquantes")

        value, used_ai = llm.write(
            "insights_dormant",
            "insights_dormant",
            data,
            ListingNotes,
            fallback,
            lambda v: [n.note for n in v.items],
            shop=shop,
            extra_validate=check,
        )
        notes = {n.listing_id: n.note for n in value.items}
    else:
        notes = {}
    for index, row in enumerate(rows):
        listing = row.pop("listing")
        row["note"] = notes.get(row["id"]) or (_fallback_note(row) if row["causes"] else "")
        needs_text = any(c["code"] in ("short_description", "missing_specs") for c in row["causes"])
        row["fix"] = None
        if with_fixes and needs_text and index < FIX_LIMIT:
            row["fix"] = correction(listing, shop)
    return {"min_days": MIN_DAYS, "rows": rows, "used_ai": used_ai}
