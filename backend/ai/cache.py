import hashlib
import json
from datetime import timedelta

from django.utils import timezone

from .models import AICache

TTL = {
    "search": timedelta(hours=24),
    "compare": timedelta(days=7),
    "assistant": timedelta(hours=24),
}


def make_key(feature: str, inputs) -> str:
    """Stable hash of the feature and its normalised inputs."""
    normalised = json.dumps(inputs, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{feature}:{normalised}".encode()).hexdigest()


def get(key: str):
    row = AICache.objects.filter(key=key, expires_at__gt=timezone.now()).first()
    return row.value if row else None


def put(key: str, feature: str, value, ttl: timedelta | None = None) -> None:
    ttl = ttl or TTL.get(feature, timedelta(hours=24))
    AICache.objects.update_or_create(
        key=key,
        defaults={"feature": feature, "value": value, "expires_at": timezone.now() + ttl},
    )


def purge_expired() -> int:
    deleted, _ = AICache.objects.filter(expires_at__lte=timezone.now()).delete()
    return deleted
