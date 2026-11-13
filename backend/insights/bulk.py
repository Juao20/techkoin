"""P6, « Optimisation des annonces en lot »: F2 on 1 to 50 listings, validated before and after.

Nothing is written by `propose()`. The shop reviews each before/after pair and `apply()` writes
only the accepted ones, only on its own listings.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections, transaction

from ai import client, describe
from marketplace import services
from marketplace.models import Listing

MAX_BATCH = 50
EDITABLE = (Listing.Status.ACTIVE, Listing.Status.DRAFT, Listing.Status.PENDING_REVIEW)


class BulkError(ValueError):
    pass


def _owned(shop, ids) -> list[Listing]:
    if not isinstance(ids, list) or not ids:
        raise BulkError("Sélectionnez au moins une annonce.")
    if len(ids) > MAX_BATCH:
        raise BulkError(f"Sélectionnez {MAX_BATCH} annonces au maximum.")
    try:
        wanted = {int(i) for i in ids}
    except (TypeError, ValueError):
        raise BulkError("Sélection invalide.") from None
    found = list(
        Listing.objects.filter(shop=shop, pk__in=wanted, status__in=EDITABLE)
        .select_related("device_model", "brand", "processor", "gpu")
        .order_by("id")
    )
    if len(found) != len(wanted):
        raise BulkError(
            "Certaines annonces ne peuvent pas être optimisées (introuvables ou vendues)."
        )
    return found


def _one(listing: Listing, user) -> dict:
    text = describe.run(listing, user=user)
    return {
        "listing_id": listing.pk,
        "slug": listing.slug,
        "before": {"title": listing.title, "description": listing.description},
        "after": {"title": text["title"], "description": text["description"]},
        "highlights": text["highlights"],
        "used_ai": text["used_ai"],
    }


def propose(shop, ids) -> list[dict]:
    listings = _owned(shop, ids)
    user = shop.owner
    if not client.has_key():  # templates only: no network, no need for threads
        return [_one(x, user) for x in listings]

    def task(listing):
        try:
            return _one(listing, user)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(task, listings))


@transaction.atomic
def apply(shop, items) -> list[int]:
    if not isinstance(items, list) or not items:
        raise BulkError("Aucune modification à appliquer.")
    if len(items) > MAX_BATCH:
        raise BulkError(f"{MAX_BATCH} annonces au maximum.")
    by_id = {x.pk: x for x in _owned(shop, [i.get("listing_id") for i in items])}
    done = []
    for item in items:
        listing = by_id[int(item["listing_id"])]
        title = str(item.get("title", "")).strip()
        description = str(item.get("description", "")).strip()
        if not title or len(title) > 120:
            raise BulkError("Un titre est vide ou dépasse 120 caractères.")
        if not description:
            raise BulkError("Une description est vide.")
        listing.title = title
        listing.description = description
        listing.moderation_flags = {**listing.moderation_flags, "auto_title": False}
        services.refresh_search_text(listing)
        listing.save(
            update_fields=["title", "description", "search_text", "moderation_flags", "updated_at"]
        )
        done.append(listing.pk)
    return done
