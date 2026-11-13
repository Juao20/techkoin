"""F5: AI comparison. Django computes the table and a deterministic verdict; the model may only
rephrase and arbitrate from that data, and its answer is checked before it is shown."""

from __future__ import annotations

from django.conf import settings

from pricing import compare as calc

from . import cache, client, describe
from .schemas import CompareVerdict


def _clean(verdict: dict) -> dict:
    return {k: v for k, v in verdict.items() if not k.startswith("_")}


def run(ids: list[int], usage: str | None, budget: int | None, user=None) -> dict:
    listings = calc.load(ids)
    category = listings[0].category
    if usage and usage not in calc.usages_for(category):
        raise calc.CompareError("Cet usage ne s'applique pas à cette catégorie d'appareils.")
    rows = calc.table(listings)

    key = cache.make_key(
        "compare",
        {
            "ids": sorted(x.pk for x in listings),
            "usage": usage,
            "budget": budget,
            "versions": [x.updated_at.isoformat() for x in sorted(listings, key=lambda x: x.pk)],
        },
    )
    if (hit := cache.get(key)) is not None:
        client._log("compare", user, None, success=True, cache_hit=True)
        return hit

    deterministic = calc.deterministic_verdict(listings, usage, budget)
    ids_set = {x.pk for x in listings}
    data = {
        "annonces": [
            {
                "id": x.pk,
                "titre": x.title,
                "prix_fcfa": x.price_fcfa,
                "note": calc.score(x, usage, budget),
            }
            for x in listings
        ],
        "tableau": [r.as_dict() for r in rows],
        "usage_choisi": calc.USAGE_LABEL.get(usage or "", None),
        "budget_max_fcfa": budget,
        "verdict_deterministe": _clean(deterministic),
        "alertes": {x.pk: calc.warnings(x, budget) for x in listings},
    }
    allowed = {n.replace(",", ".") for n in describe._numbers(data)}

    def validate(v: CompareVerdict) -> None:
        if v.winner_listing_id not in ids_set:
            raise ValueError("gagnant absent de la comparaison")
        if {p.listing_id for p in v.per_listing} != ids_set:
            raise ValueError("verdicts par annonce incomplets")
        if len(v.summary.split()) > 60:
            raise ValueError("résumé trop long")
        text = " ".join(
            [v.summary, *v.reasons, *v.warnings, *(p.verdict_line for p in v.per_listing)]
        )
        invented = {n.replace(",", ".") for n in describe._numbers(text)} - allowed
        if invented:
            raise ValueError(f"chiffres inventés : {sorted(invented)}")

    result = client.complete(
        "compare",
        "compare",
        {"data": data},
        CompareVerdict,
        "smart",
        fallback=lambda: CompareVerdict.model_validate(_clean(deterministic)),
        user=user,
        timeout=settings.AI_COMPARE_TIMEOUT_SECONDS,
        validate=validate,
    )
    payload = {
        "rows": [r.as_dict() for r in rows],
        "verdict": result.value.model_dump(),
        "used_ai": not result.fallback_used,
        "usage": usage,
        "budget": budget,
        "listing_ids": [x.pk for x in listings],
    }
    cache.put(key, "compare", payload)
    return payload
