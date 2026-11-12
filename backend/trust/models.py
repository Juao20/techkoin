from django.conf import settings
from django.db import models

from marketplace.models import Listing


class StolenDeviceReport(models.Model):
    """A declared stolen device. Only confirmed reports block a publication."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        CONFIRMED = "confirmed", "Confirmé"
        DISMISSED = "dismissed", "Rejeté"

    imei_or_serial_hash = models.CharField(max_length=64, db_index=True)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    description = models.TextField()
    police_reference = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Appareil déclaré volé #{self.pk} ({self.get_status_display()})"


class ModerationQueueItem(Listing):
    """Listings waiting for a moderator, shown as their own entry in the admin."""

    class Meta:
        proxy = True
        verbose_name = "annonce à modérer"
        verbose_name_plural = "file de modération"


class ModerationDecision(models.Model):
    class Action(models.TextChoices):
        APPROVE = "approve", "Approuver"
        REJECT = "reject", "Refuser"
        REQUEST_CHANGES = "request_changes", "Demander des modifications"

    listing = models.ForeignKey(
        "marketplace.Listing", on_delete=models.CASCADE, related_name="decisions"
    )
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
