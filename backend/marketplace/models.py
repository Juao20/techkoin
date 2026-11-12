from django.conf import settings
from django.db import models

from catalog.models import Brand, Category, DeviceModel, GraphicsCard, Processor

from .crypto import EncryptedTextField


class Listing(models.Model):
    class Condition(models.TextChoices):
        NEW_SEALED = "new_sealed", "Neuf scellé"
        NEW_OPEN = "new_open", "Neuf ouvert"
        REFURBISHED = "refurbished", "Reconditionné"
        USED = "used", "Occasion"

    class Grade(models.TextChoices):
        A = "A", "Comme neuf"
        B = "B", "Bon état"
        C = "C", "Traces visibles"

    class Provenance(models.TextChoices):
        LOCAL = "local", "Locale"
        EUROPE = "europe", "Europe"
        USA = "usa", "États-Unis"
        DUBAI = "dubai", "Dubaï"
        CHINA = "china", "Chine"
        OTHER = "other", "Autre"

    class ImeiStatus(models.TextChoices):
        UNCHECKED = "unchecked", "Non vérifié"
        OK = "ok", "Valide"
        DUPLICATE = "duplicate", "Doublon"
        REPORTED_STOLEN = "reported_stolen", "Déclaré volé"
        INVALID = "invalid", "Invalide"

    class StorageType(models.TextChoices):
        SSD = "ssd", "SSD"
        HDD = "hdd", "HDD"
        HYBRID = "hybrid", "Hybride"
        EMMC = "emmc", "eMMC"
        UFS = "ufs", "UFS"

    class PriceBadge(models.TextChoices):
        GOOD_DEAL = "good_deal", "Bonne affaire"
        FAIR = "fair", "Prix correct"
        ABOVE_MARKET = "above_market", "Au-dessus du marché"
        UNKNOWN = "unknown", "Inconnu"

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PENDING_REVIEW = "pending_review", "En modération"
        ACTIVE = "active", "En ligne"
        RESERVED = "reserved", "Réservée"
        SOLD = "sold", "Vendue"
        REJECTED = "rejected", "Refusée"
        ARCHIVED = "archived", "Archivée"

    class Keyboard(models.TextChoices):
        AZERTY = "azerty", "AZERTY"
        QWERTY = "qwerty", "QWERTY"
        QWERTZ = "qwertz", "QWERTZ"
        OTHER = "other", "Autre"

    # Relations
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings"
    )
    shop = models.ForeignKey(
        "accounts.Shop", null=True, blank=True, on_delete=models.SET_NULL, related_name="listings"
    )
    device_model = models.ForeignKey(
        DeviceModel, null=True, blank=True, on_delete=models.SET_NULL, related_name="listings"
    )
    custom_model_name = models.CharField(max_length=120, blank=True)

    # Identity
    category = models.CharField(max_length=12, choices=Category.choices)
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.PROTECT)
    title = models.CharField(max_length=120, blank=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    description = models.TextField(blank=True)

    # Commercial
    condition_type = models.CharField(max_length=12, choices=Condition.choices, default="used")
    grade = models.CharField(max_length=1, choices=Grade.choices, blank=True)
    price_fcfa = models.PositiveIntegerField(default=0)
    negotiable = models.BooleanField(default=False)
    city = models.CharField(max_length=80, blank=True)
    quartier = models.CharField(max_length=80, blank=True)
    accessories = models.JSONField(default=list, blank=True)
    has_invoice = models.BooleanField(default=False)
    warranty_months = models.PositiveSmallIntegerField(default=0)
    provenance = models.CharField(max_length=10, choices=Provenance.choices, blank=True)

    # Identification (never exposed publicly)
    imei_or_serial = EncryptedTextField(blank=True)
    imei_status = models.CharField(
        max_length=20, choices=ImeiStatus.choices, default=ImeiStatus.UNCHECKED
    )

    # Common specs
    ram_gb = models.PositiveSmallIntegerField(null=True, blank=True)
    storage_gb = models.PositiveIntegerField(null=True, blank=True)
    storage_type = models.CharField(max_length=10, choices=StorageType.choices, blank=True)
    color = models.CharField(max_length=40, blank=True)
    screen_size_in = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    screen_resolution = models.CharField(max_length=20, blank=True)
    refresh_rate_hz = models.PositiveSmallIntegerField(null=True, blank=True)

    # PC specs
    processor = models.ForeignKey(
        Processor, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    gpu = models.ForeignKey(
        GraphicsCard, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    gpu_dedicated = models.BooleanField(default=False)
    vram_gb = models.PositiveSmallIntegerField(null=True, blank=True)
    touchscreen = models.BooleanField(default=False)
    os = models.CharField(max_length=40, blank=True)
    keyboard_layout = models.CharField(max_length=10, choices=Keyboard.choices, blank=True)
    keyboard_backlit = models.BooleanField(default=False)
    battery_cycles = models.PositiveIntegerField(null=True, blank=True)
    battery_autonomy_h = models.PositiveSmallIntegerField(null=True, blank=True)
    ports = models.JSONField(default=list, blank=True)
    ram_upgradable = models.BooleanField(default=False)

    # Phone / tablet specs
    battery_health_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    network_5g = models.BooleanField(default=False)
    dual_sim = models.BooleanField(default=False)
    esim = models.BooleanField(default=False)
    carrier_unlocked = models.BooleanField(default=True)
    account_removed = models.BooleanField(default=False)
    biometrics_ok = models.BooleanField(default=True)
    screen_original = models.BooleanField(default=True)
    replaced_parts = models.JSONField(default=list, blank=True)
    cellular = models.BooleanField(default=False)
    stylus_included = models.BooleanField(default=False)
    keyboard_included = models.BooleanField(default=False)

    # Price and AI (computed, read only; filled from phase 2)
    estimate_low = models.PositiveIntegerField(null=True, blank=True)
    estimate_mid = models.PositiveIntegerField(null=True, blank=True)
    estimate_high = models.PositiveIntegerField(null=True, blank=True)
    estimate_sample_size = models.PositiveIntegerField(default=0)
    price_badge = models.CharField(
        max_length=14, choices=PriceBadge.choices, default=PriceBadge.UNKNOWN
    )
    usage_scores = models.JSONField(default=dict, blank=True)

    # Moderation
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    risk_score = models.PositiveSmallIntegerField(default=0)
    moderation_flags = models.JSONField(default=dict, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Counters (denormalised)
    views_count = models.PositiveIntegerField(default=0)
    contacts_count = models.PositiveIntegerField(default=0)
    favorites_count = models.PositiveIntegerField(default=0)

    published_at = models.DateTimeField(null=True, blank=True)
    sold_at = models.DateTimeField(null=True, blank=True)
    last_price_change_at = models.DateTimeField(null=True, blank=True)
    is_boosted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "category", "-published_at"]),
            models.Index(fields=["status", "price_fcfa"]),
            models.Index(fields=["city"]),
        ]

    def __str__(self):
        return self.title or f"Annonce {self.pk}"

    @property
    def is_new(self) -> bool:
        return self.condition_type in {self.Condition.NEW_SEALED, self.Condition.NEW_OPEN}


class ListingPhoto(models.Model):
    class Kind(models.TextChoices):
        FRONT = "front", "Face avant"
        BACK = "back", "Face arrière"
        SCREEN_ON = "screen_on", "Écran allumé"
        DEFECT = "defect", "Défaut"
        OTHER = "other", "Autre"

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="listings/%Y/%m/")
    thumb = models.ImageField(upload_to="listings/thumbs/%Y/%m/")
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.OTHER)
    position = models.PositiveSmallIntegerField(default=0)
    phash = models.CharField(max_length=32, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "id"]


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "listing"], name="unique_favorite")]
