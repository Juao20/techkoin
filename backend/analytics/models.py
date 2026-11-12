from django.conf import settings
from django.db import models


class Event(models.Model):
    class Type(models.TextChoices):
        SEARCH = "search"
        SEARCH_NO_RESULT = "search_no_result"
        LISTING_VIEW = "listing_view"
        CONTACT_CLICK = "contact_click"
        WHATSAPP_CLICK = "whatsapp_click"
        PHONE_REVEAL = "phone_reveal"
        FAVORITE_ADD = "favorite_add"
        COMPARE = "compare"
        CHECKOUT_START = "checkout_start"
        ORDER_PAID = "order_paid"
        AI_SEARCH = "ai_search"
        AI_ASSISTANT_QUESTION = "ai_assistant_question"
        ALERT_CREATED = "alert_created"

    type = models.CharField(max_length=24, choices=Type.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    session_id = models.CharField(max_length=40, blank=True)
    listing = models.ForeignKey(
        "marketplace.Listing", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    shop = models.ForeignKey(
        "accounts.Shop", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    query_text = models.CharField(max_length=200, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    results_count = models.PositiveIntegerField(null=True, blank=True)
    city = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["type", "created_at"]),
            models.Index(fields=["listing", "type"]),
            models.Index(fields=["shop", "type", "created_at"]),
        ]
