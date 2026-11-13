from django.conf import settings
from django.db import models


class AIRequestLog(models.Model):
    """One row per call to a feature, whether Groq answered or the fallback did."""

    feature = models.CharField(max_length=40, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    shop = models.ForeignKey(
        "accounts.Shop", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    model = models.CharField(max_length=80, blank=True)
    prompt_version = models.CharField(max_length=20, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    success = models.BooleanField(default=True)
    fallback_used = models.BooleanField(default=False)
    cache_hit = models.BooleanField(default=False)
    error = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["feature", "created_at"])]


class AICache(models.Model):
    """Answers kept for a while; the key hashes the feature and its normalised inputs."""

    key = models.CharField(max_length=64, unique=True)
    feature = models.CharField(max_length=40, db_index=True)
    value = models.JSONField()
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
