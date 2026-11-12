"""Keeps the computed fields of a listing (estimate, badge, usage scores) up to date."""

from .estimate import estimate_listing, price_badge
from .usage import usage_scores

COMPUTED_FIELDS = [
    "estimate_low",
    "estimate_mid",
    "estimate_high",
    "estimate_sample_size",
    "price_badge",
    "usage_scores",
    "updated_at",
]


def recompute_listing(listing, save: bool = True):
    est = estimate_listing(listing)
    listing.estimate_low = est.low if est else None
    listing.estimate_mid = est.mid if est else None
    listing.estimate_high = est.high if est else None
    listing.estimate_sample_size = est.sample_size if est else 0
    listing.price_badge = price_badge(listing.price_fcfa, est)
    listing.usage_scores = usage_scores(listing)
    flags = dict(listing.moderation_flags or {})
    flags["estimate_indicative"] = bool(est.indicative) if est else True
    listing.moderation_flags = flags
    if save:
        listing.save(update_fields=[*COMPUTED_FIELDS, "moderation_flags"])
    return est
