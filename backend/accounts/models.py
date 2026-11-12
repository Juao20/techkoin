from django.contrib.auth.models import AbstractUser
from django.db import models


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
    identity_document = models.FileField(upload_to=identity_document_path, blank=True)
    is_moderator = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_username()
