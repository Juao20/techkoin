"""P2, « Conseiller prix »: for each active listing, where its price stands and what to ask.

The advised price is computed here from the listing's market estimate (rounded to 5 000 FCFA);
the model only words the explanation and can never change the figure.
"""

from __future__ import annotations

from django.utils import timezone

from marketplace.models import Listing
from pricing.estimate import round_price

from . import llm, market
from .schemas import ListingNotes

HIGH = 0.10  # above the estimate by more than this: lower the price
LOW = -0.10  # below the estimate by more than this: money left on the table
TARGET_WHEN_HIGH = 1.05
TARGET_WHEN_LOW = 0.97


def advise(listing: Listing) -> dict:
    """Deterministic advice for one listing."""
    mid = listing.estimate_mid
    if not mid:
        return {"action": "none", "advised_price_fcfa": None, "gap_pct": None, "indicative": True}
    gap = round((listing.price_fcfa - mid) * 100 / mid)
    ratio = listing.price_fcfa / mid - 1
    # An estimate built from fewer than 5 comparables is only indicative: wider margin.
    indicative = listing.estimate_sample_size < 5
    high, low = (HIGH * 2.5, LOW * 2.5) if indicative else (HIGH, LOW)
    if ratio > high:
        action, advised = "lower", round_price(mid * TARGET_WHEN_HIGH)
    elif ratio < low:
        action, advised = "raise", round_price(mid * TARGET_WHEN_LOW)
    else:
        action, advised = "keep", listing.price_fcfa
    if action != "keep" and advised == round_price(listing.price_fcfa):
        action, advised = "keep", listing.price_fcfa
    return {
        "action": action,
        "advised_price_fcfa": advised,
        "gap_pct": gap,
        "indicative": indicative,
    }


def _fallback_note(row: dict) -> str:
    gap, advised = row["gap_pct"], row["advised_price_fcfa"]
    if row["action"] == "lower":
        return (
            f"Votre prix est {gap} % au-dessus de l'estimation du marché : "
            f"{advised:,} FCFA le place dans la fourchette des acheteurs.".replace(",", " ")
        )
    if row["action"] == "raise":
        return (
            f"Votre prix est {abs(gap)} % sous l'estimation du marché : vous pouvez demander "
            f"{advised:,} FCFA sans sortir de la fourchette.".replace(",", " ")
        )
    if row["action"] == "keep":
        return "Votre prix est cohérent avec l'estimation du marché."
    return "Pas assez d'annonces comparables pour estimer ce modèle."


def rows(shop, days: int = 30) -> list[dict]:
    from analytics import stats

    activity = {r["id"]: r for r in stats.listing_rows(shop, days)}
    reference = market.category_reference(days)
    now = timezone.now()
    out = []
    for listing in Listing.objects.filter(shop=shop, status=Listing.Status.ACTIVE).order_by("id"):
        stat = activity.get(listing.pk, {})
        ref = reference.get(listing.category, {})
        advice = advise(listing)
        out.append(
            {
                "id": listing.pk,
                "slug": listing.slug,
                "title": listing.title,
                "category": listing.category,
                "price_fcfa": listing.price_fcfa,
                "estimate_fcfa": listing.estimate_mid,
                "estimate_low_fcfa": listing.estimate_low,
                "estimate_high_fcfa": listing.estimate_high,
                "estimate_sample_size": listing.estimate_sample_size,
                "price_badge": listing.price_badge,
                "days_online": max((now - (listing.published_at or listing.created_at)).days, 0),
                "views": stat.get("views", 0),
                "contacts": stat.get("contacts", 0),
                "category_avg_views": ref.get("avg_views", 0),
                "category_avg_contacts": ref.get("avg_contacts", 0),
                **advice,
            }
        )
    # Listings that need a decision first: biggest gap, either way.
    out.sort(key=lambda r: (r["action"] in ("keep", "none"), -abs(r["gap_pct"] or 0), r["id"]))
    return out


def with_notes(shop, items: list[dict], limit: int = 12) -> tuple[list[dict], bool]:
    """Attach a short explanation to the listings that call for a change."""
    todo = [r for r in items if r["action"] in ("lower", "raise")][:limit]
    data = [
        {
            k: r[k]
            for k in (
                "id",
                "title",
                "price_fcfa",
                "estimate_fcfa",
                "gap_pct",
                "advised_price_fcfa",
                "days_online",
                "views",
                "contacts",
                "category_avg_views",
                "category_avg_contacts",
            )
        }
        for r in todo
    ]
    notes: dict[int, str] = {}
    used_ai = False
    if data:
        ids = {r["id"] for r in todo}

        def fallback() -> ListingNotes:
            return ListingNotes(
                items=[{"listing_id": r["id"], "note": _fallback_note(r)} for r in todo]
            )

        def check(value: ListingNotes) -> None:
            if {n.listing_id for n in value.items} != ids:
                raise ValueError("annonces manquantes")

        value, used_ai = llm.write(
            "insights_pricing",
            "insights_pricing",
            data,
            ListingNotes,
            fallback,
            lambda v: [n.note for n in v.items],
            shop=shop,
            extra_validate=check,
        )
        notes = {n.listing_id: n.note for n in value.items}
    for r in items:
        r["note"] = notes.get(r["id"]) or _fallback_note(r)
    return items, used_ai
