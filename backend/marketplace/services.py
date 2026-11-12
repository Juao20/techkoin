"""Business rules for listings: titles, search text, publication checks."""

from django.utils import timezone
from django.utils.text import slugify

from catalog.models import Category

from .models import Listing, ListingPhoto

ACTIVE_LIMIT_PARTICULIER = 5
MIN_PHOTOS = 4
MAX_PHOTOS = 10
REQUIRED_PHOTO_KINDS = (
    ListingPhoto.Kind.FRONT,
    ListingPhoto.Kind.BACK,
    ListingPhoto.Kind.SCREEN_ON,
)
LIVE_STATUSES = (
    Listing.Status.ACTIVE,
    Listing.Status.PENDING_REVIEW,
    Listing.Status.RESERVED,
)


def format_storage(gb: int | None, kind: str = "") -> str:
    if not gb:
        return ""
    size = f"{gb // 1000} To" if gb >= 1000 and gb % 1000 == 0 else f"{gb} Go"
    return f"{size} {kind.upper()}".strip() if kind in {"ssd", "hdd"} else size


def model_label(listing: Listing) -> str:
    if listing.device_model:
        return str(listing.device_model)
    return " ".join(
        p for p in (listing.brand.name if listing.brand else "", listing.custom_model_name) if p
    )


def build_title(listing: Listing) -> str:
    parts = [model_label(listing)]
    if listing.category in (Category.SMARTPHONE, Category.TABLET) and listing.storage_gb:
        parts.append(format_storage(listing.storage_gb))
    elif listing.ram_gb:
        parts.append(f"{listing.ram_gb} Go")
        parts.append(format_storage(listing.storage_gb, listing.storage_type))
    return " ".join(p for p in parts if p)[:120]


def specs_line(listing: Listing) -> str:
    """Key specs for cards, e.g. '16 Go · 512 Go SSD · i5 11e gén.'"""
    bits: list[str] = []
    if listing.category in (Category.LAPTOP, Category.DESKTOP):
        if listing.ram_gb:
            bits.append(f"{listing.ram_gb} Go")
        if listing.storage_gb:
            bits.append(format_storage(listing.storage_gb, listing.storage_type))
        cpu = listing.processor
        if cpu:
            gen = (
                f" {cpu.generation}e gén." if cpu.family.startswith("i") and cpu.generation else ""
            )
            bits.append(f"{cpu.family}{gen}")
    else:
        if listing.storage_gb:
            bits.append(format_storage(listing.storage_gb))
        if listing.battery_health_pct:
            bits.append(f"batterie {listing.battery_health_pct} %")
    return " · ".join(bits)


def refresh_search_text(listing: Listing) -> None:
    aliases = " ".join(listing.device_model.aliases) if listing.device_model else ""
    category_label = Category(listing.category).label if listing.category else ""
    listing.search_text = " ".join(
        [listing.title, model_label(listing), aliases, category_label, listing.color]
    ).lower()


def unique_slug(listing: Listing) -> str:
    base = slugify(listing.title)[:120] or "annonce"
    slug, n = base, 2
    while Listing.objects.filter(slug=slug).exclude(pk=listing.pk).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def validate_for_publish(listing: Listing) -> dict[str, str]:
    """Return {field: message} in French. Empty means the listing can be published."""
    errors: dict[str, str] = {}
    if not (listing.device_model or (listing.brand and listing.custom_model_name)):
        errors["device_model"] = "Choisissez un modèle dans la liste ou saisissez le vôtre."
    if listing.price_fcfa <= 0:
        errors["price_fcfa"] = "Indiquez un prix en FCFA."
    if not listing.city:
        errors["city"] = "Indiquez la ville où se trouve l'appareil."
    if not listing.is_new and not listing.grade:
        errors["grade"] = "Choisissez la note d'état de l'appareil."
    from trust.imei import validate_identifier

    message = validate_identifier(
        listing.imei_or_serial, listing.category, listing.brand.slug if listing.brand else ""
    )
    if message:
        errors["imei_or_serial"] = message
    if listing.category in (Category.SMARTPHONE, Category.TABLET) and not listing.account_removed:
        errors["account_removed"] = (
            "Un appareil encore lié à un compte iCloud ou Google "
            "ne peut pas être vendu sur TechKoin."
        )
    photos = list(listing.photos.all())
    kinds = {p.kind for p in photos}
    if len(photos) < MIN_PHOTOS:
        errors["photos"] = f"Ajoutez au moins {MIN_PHOTOS} photos pour continuer."
    else:
        labels = {
            ListingPhoto.Kind.FRONT: "face avant",
            ListingPhoto.Kind.BACK: "face arrière",
            ListingPhoto.Kind.SCREEN_ON: "écran allumé",
        }
        missing = [labels[k] for k in REQUIRED_PHOTO_KINDS if k not in kinds]
        if missing:
            errors["photos"] = f"Photo manquante : {', '.join(missing)}. Ajoutez-la pour continuer."
        elif (
            listing.grade == Listing.Grade.C or listing.moderation_flags.get("declared_defect")
        ) and ListingPhoto.Kind.DEFECT not in kinds:
            errors["photos"] = "Une photo du défaut est obligatoire. Ajoutez-la pour continuer."
    return errors


def active_count(user) -> int:
    return Listing.objects.filter(seller=user, status__in=LIVE_STATUSES).count()


def publish(listing: Listing) -> Listing:
    """Move a validated listing online (or to review for models outside the catalog)."""
    from pricing.services import recompute_listing
    from trust.services import evaluate_publication

    recompute_listing(listing, save=False)
    outcome = evaluate_publication(listing)
    listing.imei_status = outcome.imei_status
    listing.risk_score = outcome.score
    flags = {
        k: v for k, v in listing.moderation_flags.items() if k not in {"risk_rules", "priority"}
    }
    flags["risk_rules"] = outcome.rules
    if outcome.priority:
        flags["priority"] = True
    if listing.device_model is None:
        flags["custom_model"] = True
    listing.moderation_flags = flags
    listing.status = Listing.Status.PENDING_REVIEW if outcome.review else Listing.Status.ACTIVE
    listing.published_at = listing.published_at or timezone.now()
    listing.save()
    return listing
