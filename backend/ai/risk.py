"""F6: AI scam signal. It reads the listing text and may add up to 25 risk points.

It never blocks on its own: 25 is below the review threshold, and the rule based engine
(trust/risk.py) stays in charge. Without a model the signal is simply 0.
"""

from __future__ import annotations

from marketplace.models import Listing

from . import client, describe, privacy
from .schemas import RiskSignal


def signal(listing: Listing) -> RiskSignal:
    text = privacy.scrub_text(f"{listing.title}. {listing.description}".strip())
    if len(text) < 15 and not listing.description:
        return RiskSignal(risk=0)  # nothing to read
    result = client.complete(
        "risk",
        "risk",
        {"facts": describe.facts(listing), "price_fcfa": listing.price_fcfa, "text": text},
        RiskSignal,
        "fast",
        fallback=lambda: RiskSignal(risk=0),
        user=listing.seller,
    )
    value = result.value
    value.signals = [privacy.scrub_text(s)[:120] for s in value.signals]
    return value
