"""F4: the buyer assistant on every listing page.

It answers from the listing's data only (specs, usage scores, estimate, trust signals) and says
so when the data does not contain the answer.
"""

from __future__ import annotations

from marketplace.models import Listing

from . import cache, client, describe, privacy
from .fallback import assistant as rules
from .schemas import AssistantAnswer

MAX_HISTORY = 5
MAX_QUESTION = 300


def context(listing: Listing) -> dict:
    """What the assistant may know. Nothing about the seller beyond public trust signals."""
    est = None
    if listing.estimate_mid:
        est = {
            "low": listing.estimate_low,
            "mid": listing.estimate_mid,
            "high": listing.estimate_high,
            "indicative": bool(listing.moderation_flags.get("estimate_indicative", True)),
        }
    return {
        "facts": describe.facts(listing),
        "grade": listing.grade or None,
        "usage_scores": listing.usage_scores or {},
        "estimate": est,
        "price_badge": listing.price_badge,
        "prix_demande_fcfa": listing.price_fcfa,
        "battery_autonomy_h": listing.battery_autonomy_h,
        "battery_cycles": listing.battery_cycles,
        "account_removed": (
            listing.account_removed if listing.category in ("smartphone", "tablet") else None
        ),
        "confiance": {
            "vendeur_verifie": bool(
                (listing.shop and listing.shop.is_verified)
                or listing.seller.identity_status == "verified"
            ),
            "imei_controle": listing.imei_status == "ok",
            "facture": listing.has_invoice,
        },
    }


def clean_history(history, names=()) -> list[str]:
    """Only the buyer's earlier questions are kept: answers sent back by a browser are not
    trusted, and free text is scrubbed of contact details and of the seller's name."""
    out = []
    for item in (history or [])[-MAX_HISTORY:]:
        question = item.get("q") if isinstance(item, dict) else item
        if question:
            text = privacy.scrub_names(privacy.scrub_text(str(question)), names)
            out.append(text[:MAX_QUESTION])
    return out


def seller_names(listing: Listing) -> list[str]:
    seller = listing.seller
    return [n for n in (seller.first_name, seller.last_name) if n]


def run(listing: Listing, question: str, history=None, user=None) -> dict:
    names = seller_names(listing)
    question = privacy.scrub_names(
        privacy.scrub_text(" ".join(question.split())[:MAX_QUESTION]), names
    )
    history = clean_history(history, names)
    ctx = context(listing)
    key = None
    if not history:  # follow-up questions depend on the conversation: only first ones are cached
        key = cache.make_key(
            "assistant",
            {"id": listing.pk, "v": listing.updated_at.isoformat(), "q": question.lower()},
        )
        if (hit := cache.get(key)) is not None:
            client._log("assistant", user, None, success=True, cache_hit=True)
            return hit

    allowed = describe.allowed_numbers(ctx["facts"]) | {
        n.replace(",", ".") for n in describe._numbers(ctx) | describe._numbers(question)
    }

    def validate(value: AssistantAnswer) -> None:
        invented = {n.replace(",", ".") for n in describe._numbers(value.answer)} - allowed
        if invented:
            raise ValueError(f"chiffres inventés : {sorted(invented)}")
        if value.information_missing and not value.suggested_seller_question:
            value.suggested_seller_question = question

    result = client.complete(
        "assistant",
        "assistant",
        {"listing": ctx, "history": history, "question": question},
        AssistantAnswer,
        "smart",
        fallback=lambda: rules.answer(question, ctx),
        user=user,
        validate=validate,
    )
    value = result.value
    payload = {
        "answer": value.answer,
        "information_missing": value.information_missing,
        "suggested_seller_question": (
            value.suggested_seller_question if value.information_missing else None
        ),
        "used_ai": not result.fallback_used,
    }
    if key:
        cache.put(key, "assistant", payload)
    return payload
