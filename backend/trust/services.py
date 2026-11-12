"""Publication checks and moderation decisions."""

from dataclasses import dataclass, field
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from . import risk
from .imei import hash_identifier
from .models import ModerationDecision, StolenDeviceReport

ACTIVE_STATES = ("active", "pending_review", "reserved")
DEFAULT_REJECTION = "Cette annonce ne respecte pas les règles de TechKoin."
DEFAULT_CHANGES = "Merci de compléter ou corriger votre annonce avant de la republier."


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


@transaction.atomic
def decide(listing, moderator, action: str, reason: str = "") -> ModerationDecision:
    """Apply a moderator's decision to a listing waiting in the queue and keep a record of it."""
    from marketplace.models import Listing

    if listing.imei_status == "reported_stolen" and action == ModerationDecision.Action.APPROVE:
        raise ValueError("Un appareil déclaré volé ne peut pas être approuvé.")
    flags = dict(listing.moderation_flags or {})
    if action == ModerationDecision.Action.APPROVE:
        listing.status = Listing.Status.ACTIVE
        listing.rejection_reason = ""
        flags["approved_by_moderator"] = True
    elif action == ModerationDecision.Action.REJECT:
        listing.status = Listing.Status.REJECTED
        listing.rejection_reason = reason or DEFAULT_REJECTION
    else:
        listing.status = Listing.Status.DRAFT
        listing.rejection_reason = reason or DEFAULT_CHANGES
    flags.pop("priority", None)
    listing.moderation_flags = flags
    listing.save(update_fields=["status", "rejection_reason", "moderation_flags", "updated_at"])
    return ModerationDecision.objects.create(
        listing=listing, moderator=moderator, action=action, reason=listing.rejection_reason
    )


DOCUMENT_RETENTION_DAYS = 90


def decide_identity(user, approve: bool) -> None:
    from accounts.models import User

    user.identity_status = (
        User.VerificationStatus.VERIFIED if approve else User.VerificationStatus.REJECTED
    )
    user.identity_decided_at = timezone.now()
    user.save(update_fields=["identity_status", "identity_decided_at", "updated_at"])


def decide_shop(shop, approve: bool) -> None:
    from accounts.models import User

    shop.verification_status = (
        User.VerificationStatus.VERIFIED if approve else User.VerificationStatus.REJECTED
    )
    shop.verification_decided_at = timezone.now()
    shop.save(update_fields=["verification_status", "verification_decided_at", "updated_at"])


def purge_old_documents() -> int:
    """Keep only the decision: delete documents 90 days after it was taken."""
    from accounts.models import Shop, User

    limit = timezone.now() - timedelta(days=DOCUMENT_RETENTION_DAYS)
    purged = 0
    for user in User.objects.filter(identity_decided_at__lte=limit).exclude(identity_document=""):
        user.identity_document.delete(save=False)
        if user.identity_selfie:
            user.identity_selfie.delete(save=False)
        user.identity_document = user.identity_selfie = ""
        user.save(update_fields=["identity_document", "identity_selfie", "updated_at"])
        purged += 1
    for shop in Shop.objects.filter(verification_decided_at__lte=limit).exclude(
        verification_document=""
    ):
        shop.verification_document.delete(save=False)
        shop.verification_document = ""
        shop.save(update_fields=["verification_document", "updated_at"])
        purged += 1
    return purged


@transaction.atomic
def confirm_stolen_report(report: StolenDeviceReport) -> int:
    """Confirm a report, then pull every live listing with that identifier out of sight."""
    from marketplace.models import Listing

    report.status = StolenDeviceReport.Status.CONFIRMED
    report.save(update_fields=["status", "updated_at"])
    hit = Listing.objects.filter(
        imei_hash=report.imei_or_serial_hash,
        status__in=[Listing.Status.ACTIVE, Listing.Status.RESERVED, Listing.Status.PENDING_REVIEW],
    )
    count = 0
    for listing in hit:
        listing.status = Listing.Status.PENDING_REVIEW
        listing.imei_status = "reported_stolen"
        listing.risk_score = 100
        listing.moderation_flags = {**listing.moderation_flags, "priority": True}
        listing.save(
            update_fields=["status", "imei_status", "risk_score", "moderation_flags", "updated_at"]
        )
        count += 1
    return count
