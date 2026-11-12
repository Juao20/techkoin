"""Encryption at rest for identifiers such as IMEI (Fernet, key from the environment)."""

import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


def _fernet() -> Fernet:
    key = settings.FIELD_ENCRYPTION_KEY
    if key:
        return Fernet(key.encode())
    # Development fallback: derive a key from SECRET_KEY. Production must set the variable.
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode() if value else ""


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode() if token else ""


def identifier_hash(value: str) -> str:
    """Stable hash used to compare identifiers without storing them in clear."""
    normalized = "".join(ch for ch in value.upper() if ch.isalnum())
    return hashlib.sha256(normalized.encode()).hexdigest()


class EncryptedTextField(models.TextField):
    """Transparent encryption: Python sees plain text, the database sees a Fernet token."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt(value) if value else value

    def from_db_value(self, value, expression, connection):
        return decrypt(value) if value else value
