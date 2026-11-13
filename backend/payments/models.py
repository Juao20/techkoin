from django.conf import settings
from django.db import models


class Order(models.Model):
    """A purchase paid into escrow (sandbox). Transitions live in payments/services.py."""

    class Status(models.TextChoices):
        CREATED = "created", "Créée"
        PAYMENT_PENDING = "payment_pending", "Paiement en cours"
        PAID_HELD = "paid_held", "Payée, fonds en séquestre"
        HANDED_OVER = "handed_over", "Appareil remis"
        RELEASED = "released", "Fonds versés au vendeur"
        DISPUTED = "disputed", "Litige ouvert"
        REFUNDED = "refunded", "Remboursée"
        CANCELLED = "cancelled", "Annulée"

    class Delivery(models.TextChoices):
        MEETUP = "meetup", "Remise en main propre"
        DELIVERY = "delivery", "Livraison"

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchases"
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales"
    )
    listing = models.ForeignKey(
        "marketplace.Listing", on_delete=models.PROTECT, related_name="orders"
    )
    amount_fcfa = models.PositiveIntegerField()
    commission_fcfa = models.PositiveIntegerField()
    seller_payout_fcfa = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.CREATED, db_index=True
    )
    delivery_mode = models.CharField(max_length=10, choices=Delivery.choices, default="meetup")
    meetup_note = models.CharField(max_length=300, blank=True)
    payment_expires_at = models.DateTimeField(null=True, blank=True)
    handed_over_at = models.DateTimeField(null=True, blank=True)
    buyer_confirmed_at = models.DateTimeField(null=True, blank=True)
    auto_release_at = models.DateTimeField(null=True, blank=True, db_index=True)
    dispute_reason = models.TextField(blank=True)
    is_sandbox = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Commande {self.pk} ({self.get_status_display()})"


class OrderEvent(models.Model):
    """History journal: one row per transition."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]


class Subscription(models.Model):
    """One month of the Pro plan, paid through a Transaction (spec 9.3). No escrow."""

    class Status(models.TextChoices):
        PENDING = "pending", "Paiement en cours"
        ACTIVE = "active", "Active"
        FAILED = "failed", "Échouée"
        EXPIRED = "expired", "Terminée"

    shop = models.ForeignKey(
        "accounts.Shop", on_delete=models.CASCADE, related_name="subscriptions"
    )
    amount_fcfa = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_sandbox = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Abonnement Pro {self.pk} ({self.shop})"

    # What a provider needs to know about the thing being paid for.
    @property
    def provider_description(self) -> str:
        return f"Abonnement Pro TechKoin {self.pk}"

    @property
    def callback_path(self) -> str:
        return "/pro/abonnement"


class Transaction(models.Model):
    class Provider(models.TextChoices):
        SIMULATOR = "simulator", "Simulateur"
        FEDAPAY = "fedapay", "FedaPay"

    class Operator(models.TextChoices):
        MTN = "mtn", "MTN MoMo"
        MOOV = "moov", "Moov Money"
        CELTIIS = "celtiis", "Celtiis Cash"

    class Direction(models.TextChoices):
        IN = "in", "Encaissement"
        OUT = "out", "Versement"
        REFUND = "refund", "Remboursement"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        SUCCEEDED = "succeeded", "Réussie"
        FAILED = "failed", "Échouée"

    order = models.ForeignKey(
        Order, null=True, blank=True, on_delete=models.PROTECT, related_name="transactions"
    )
    subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    provider = models.CharField(max_length=12, choices=Provider.choices)
    operator = models.CharField(max_length=10, choices=Operator.choices, blank=True)
    payer_phone = models.CharField(max_length=20, blank=True)
    amount_fcfa = models.PositiveIntegerField()
    direction = models.CharField(max_length=8, choices=Direction.choices)
    provider_reference = models.CharField(max_length=120, blank=True, db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    raw_payload = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
