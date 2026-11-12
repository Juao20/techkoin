"""Publication checks: IMEI status, risk score and the resulting moderation decision."""

from dataclasses import dataclass, field

from . import risk
from .imei import hash_identifier
from .models import StolenDeviceReport

ACTIVE_STATES = ("active", "pending_review", "reserved")


@dataclass
class Outcome:
    imei_status: str
    score: int
    rules: dict[str, int] = field(default_factory=dict)
    review: bool = False
    priority: bool = False


def imei_status(listing) -> str:
    """'ok', 'duplicate' or 'reported_stolen' (format errors are caught before publishing)."""
    from marketplace.models import Listing

    digest = listing.imei_hash or hash_identifier(listing.imei_or_serial)
    if not digest:
        return "unchecked"
    if StolenDeviceReport.objects.filter(
        imei_or_serial_hash=digest, status=StolenDeviceReport.Status.CONFIRMED
    ).exists():
        return "reported_stolen"
    if (
        Listing.objects.filter(imei_hash=digest, status__in=ACTIVE_STATES)
        .exclude(pk=listing.pk)
        .exclude(seller=listing.seller)
        .exists()
    ):
        return "duplicate"
    return "ok"


def evaluate_publication(listing) -> Outcome:
    status = imei_status(listing)
    score, rules = risk.evaluate(listing, status)
    stolen = status == "reported_stolen"
    if stolen:
        score = 100
    priority = stolen or score >= risk.PRIORITY_THRESHOLD
    review = priority or score >= risk.REVIEW_THRESHOLD or "custom_model" in rules
    return Outcome(imei_status=status, score=score, rules=rules, review=review, priority=priority)
