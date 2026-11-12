"""Risk engine (spec 8.3): the score is the sum of rules, each one recorded in the flags."""

import re
import unicodedata
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

RULE_POINTS = {
    "price_too_low": 35,
    "contact_in_text": 20,
    "risky_phrase": 30,
    "duplicate_photo": 40,
    "new_account_many_listings": 15,
    "custom_model": 10,
    "duplicate_imei": 40,
}
REVIEW_THRESHOLD = 40
PRIORITY_THRESHOLD = 70

PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\d[\s.-]?){8,12}(?!\d)")
URL_RE = re.compile(r"https?://|www\.|wa\.me|t\.me/|\.(?:com|net|org|bj|me)\b", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def _plain(text: str) -> str:
    stripped = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in stripped if unicodedata.category(c) != "Mn")


def has_contact_info(text: str) -> bool:
    return bool(PHONE_RE.search(text) or URL_RE.search(text) or EMAIL_RE.search(text))


def has_risky_phrase(text: str) -> bool:
    plain = _plain(text)
    return any(_plain(p) in plain for p in settings.RISK_PHRASES)


def _duplicate_photo(listing) -> bool:
    from marketplace.models import ListingPhoto

    hashes = [p.phash for p in listing.photos.all() if p.phash]
    if not hashes:
        return False
    return (
        ListingPhoto.objects.filter(phash__in=hashes)
        .exclude(listing=listing)
        .exclude(listing__seller=listing.seller)
        .exclude(listing__status__in=["draft", "archived", "rejected"])
        .exists()
    )


def _new_account_many_listings(listing) -> bool:
    from marketplace.models import Listing

    seller = listing.seller
    if timezone.now() - seller.date_joined >= timedelta(hours=24):
        return False
    return Listing.objects.filter(seller=seller).exclude(status="draft").count() + 1 >= 3


def evaluate(listing, imei_status: str) -> tuple[int, dict[str, int]]:
    """Return (score 0-100, {rule: points}) for a listing about to be published."""
    rules: dict[str, int] = {}
    estimate_reliable = listing.estimate_mid and not listing.moderation_flags.get(
        "estimate_indicative", True
    )
    if estimate_reliable and listing.price_fcfa < 0.6 * listing.estimate_mid:
        rules["price_too_low"] = RULE_POINTS["price_too_low"]
    text = f"{listing.title} {listing.description}"
    if has_contact_info(text):
        rules["contact_in_text"] = RULE_POINTS["contact_in_text"]
    if has_risky_phrase(text):
        rules["risky_phrase"] = RULE_POINTS["risky_phrase"]
    if _duplicate_photo(listing):
        rules["duplicate_photo"] = RULE_POINTS["duplicate_photo"]
    if _new_account_many_listings(listing):
        rules["new_account_many_listings"] = RULE_POINTS["new_account_many_listings"]
    if listing.device_model_id is None:
        rules["custom_model"] = RULE_POINTS["custom_model"]
    if imei_status == "duplicate":
        rules["duplicate_imei"] = RULE_POINTS["duplicate_imei"]
    return min(100, sum(rules.values())), rules
