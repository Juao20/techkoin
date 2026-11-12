from django.contrib.auth.models import AbstractUser
from django.db import models

from trust.storage import PrivateStorage

private_storage = PrivateStorage()


def identity_document_path(instance, filename):
    return f"identity/{instance.pk}/{filename}"


class User(AbstractUser):
    """Custom user, defined from the start so AUTH_USER_MODEL never has to be swapped."""

    class AccountType(models.TextChoices):
        PARTICULIER = "particulier", "Particulier"
        BOUTIQUE = "boutique", "Boutique"

    class VerificationStatus(models.TextChoices):
        NONE = "none", "Non vérifié"
        PENDING = "pending", "En cours"
        VERIFIED = "verified", "Vérifié"
        REJECTED = "rejected", "Refusé"

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.PARTICULIER
    )
    city = models.CharField(max_length=80, blank=True)
    quartier = models.CharField(max_length=80, blank=True)
    phone_verified = models.BooleanField(default=False)
    identity_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.NONE
    )
    identity_document = models.FileField(
        upload_to=identity_document_path, storage=private_storage, blank=True
    )
    identity_selfie = models.FileField(
        upload_to=identity_document_path, storage=private_storage, blank=True
    )
    identity_decided_at = models.DateTimeField(null=True, blank=True)
    is_moderator = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_username()


class Shop(models.Model):
    class Plan(models.TextChoices):
        FREE = "free", "Gratuit"
        PRO = "pro", "Pro"

    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="shop")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    logo = models.ImageField(upload_to="shops/logos/", blank=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=80, blank=True)
    quartier = models.CharField(max_length=80, blank=True)
    opening_hours = models.JSONField(default=dict, blank=True)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    ifu = models.CharField(max_length=40, blank=True)
    rccm = models.CharField(max_length=40, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=User.VerificationStatus.choices,
        default=User.VerificationStatus.NONE,
    )
    verification_document = models.FileField(
        upload_to="shops/%Y/%m/", storage=private_storage, blank=True
    )
    verification_decided_at = models.DateTimeField(null=True, blank=True)
    plan = models.CharField(max_length=10, choices=Plan.choices, default=Plan.FREE)
    plan_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def is_verified(self) -> bool:
        return self.verification_status == User.VerificationStatus.VERIFIED
