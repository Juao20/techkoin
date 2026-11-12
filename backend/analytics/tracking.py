"""Single entry point for event tracking: analytics.track(type, request, **data)."""

import uuid
from datetime import timedelta

from django.utils import timezone

from .models import Event

SESSION_COOKIE = "tk_sid"
BOT_MARKERS = ("bot", "crawler", "spider", "slurp", "headless", "curl/", "python-requests")
VIEW_WINDOW = timedelta(minutes=30)


def is_bot(request) -> bool:
    agent = request.META.get("HTTP_USER_AGENT", "").lower()
    return any(marker in agent for marker in BOT_MARKERS)


def session_id(request) -> str:
    return getattr(request, "tk_sid", "") or request.COOKIES.get(SESSION_COOKIE, "")


def new_session_id() -> str:
    return uuid.uuid4().hex


def track(event_type: str, request, **data) -> Event | None:
    """Record an event. Returns None for bots and for repeated views within 30 minutes."""
    if is_bot(request):
        return None
    sid = session_id(request)
    listing = data.get("listing")
    if event_type == Event.Type.LISTING_VIEW and listing is not None:
        since = timezone.now() - VIEW_WINDOW
        if Event.objects.filter(
            type=event_type, listing=listing, session_id=sid, created_at__gte=since
        ).exists():
            return None
    user = (
        request.user if getattr(request, "user", None) and request.user.is_authenticated else None
    )
    shop = data.pop("shop", None)
    if shop is None and listing is not None:
        shop = listing.shop
    return Event.objects.create(type=event_type, user=user, session_id=sid, shop=shop, **data)
