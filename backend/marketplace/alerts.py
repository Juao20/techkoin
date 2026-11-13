"""Search alerts (spec 19, phase 6): in-app notification and e-mail, WhatsApp ready.

`run_alerts()` is the scheduled job: for every active alert it looks for listings published since
the last notification that the saved filters match, tells the user once, and moves the cursor.
Running it twice in a row never sends twice.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from analytics.models import Event
from analytics.tracking import record

from .models import Listing, Notification, SavedSearch
from .search import search_listings

logger = logging.getLogger(__name__)

MAX_ALERTS = 10
SHOWN = 3  # listings named in a message
FILTER_KEYS = {
    "q", "category", "brand", "price_min", "price_max", "condition", "grade", "ram_min",
    "storage_min", "storage_type", "gpu_dedicated", "keyboard", "os", "screen_min", "screen_max",
    "cpu_family", "cpu_gen_min", "battery_min", "5g", "dual_sim", "unlocked", "no_replaced_parts",
    "cellular", "stylus", "verified", "seller_type", "warranty", "invoice", "usage",
    "secure_payment", "city",
}  # fmt: skip


class AlertError(ValueError):
    pass


def clean_filters(raw) -> dict[str, str]:
    """Keep the known search parameters only (no page, sort or view), as strings."""
    if not isinstance(raw, dict):
        return {}
    return {k: str(v).strip()[:200] for k, v in raw.items() if k in FILTER_KEYS and str(v).strip()}


def default_name(filters: dict) -> str:
    parts = [filters.get("q"), filters.get("category"), filters.get("brand")]
    label = " ".join(p for p in parts if p) or "Appareils"
    if filters.get("price_max", "").isdigit():
        label += " jusqu'à " + f"{int(filters['price_max']):,}".replace(",", " ") + " FCFA"
    if filters.get("city"):
        label += f", {filters['city']}"
    return label[:120]


def create(user, filters: dict, name: str = "", channel: str = "email") -> SavedSearch:
    filters = clean_filters(filters)
    if not filters:
        raise AlertError("Choisissez au moins un critère de recherche avant de créer une alerte.")
    if channel not in SavedSearch.Channel.values:
        raise AlertError("Canal inconnu.")
    if SavedSearch.objects.filter(user=user).count() >= MAX_ALERTS:
        raise AlertError(f"Vous pouvez avoir {MAX_ALERTS} alertes au maximum.")
    existing = SavedSearch.objects.filter(user=user, filters=filters, is_active=True).first()
    if existing:
        return existing
    alert = SavedSearch.objects.create(
        user=user,
        name=(name or default_name(filters)).strip()[:120],
        filters=filters,
        channel=channel,
        last_notified_at=timezone.now(),  # only listings published from now on
    )
    record(Event.Type.ALERT_CREATED, user=user, filters=filters)
    return alert


def search_url(filters: dict) -> str:
    return f"/recherche?{urlencode(filters)}"


# ----------------------------------------------------------------------------- channels


class Sender(ABC):
    channel: str

    @abstractmethod
    def send(self, alert: SavedSearch, title: str, body: str, url: str) -> bool: ...


class EmailSender(Sender):
    channel = SavedSearch.Channel.EMAIL

    def send(self, alert, title, body, url):
        if not alert.user.email:
            return False
        link = f"{settings.SITE_URL}{url}"
        text = f"Bonjour,\n\n{body}\n\nVoir les annonces : {link}\n\nL'équipe TechKoin"
        return bool(
            send_mail(
                title, text, settings.DEFAULT_FROM_EMAIL, [alert.user.email], fail_silently=False
            )
        )


class WhatsAppSender(Sender):
    """Interface ready: the integration comes later. Until then the in-app notification stands."""

    channel = SavedSearch.Channel.WHATSAPP

    def send(self, alert, title, body, url):
        logger.info("WhatsApp alerts are not available yet (alert %s)", alert.pk)
        return False


SENDERS: dict[str, Sender] = {s.channel: s for s in (EmailSender(), WhatsAppSender())}


# ----------------------------------------------------------------------------- job


def new_matches(alert: SavedSearch):
    since = alert.last_notified_at or alert.created_at
    return (
        search_listings(alert.filters)
        .filter(status=Listing.Status.ACTIVE, published_at__gt=since)
        .exclude(seller=alert.user)
        .order_by("-published_at")
    )


def notify(alert: SavedSearch, listings: list[Listing], total: int) -> None:
    names = ", ".join(x.title for x in listings[:SHOWN])
    more = f" et {total - SHOWN} autre(s)" if total > SHOWN else ""
    title = (
        f"1 nouvelle annonce pour « {alert.name} »"
        if total == 1
        else f"{total} nouvelles annonces pour « {alert.name} »"
    )
    body = f"{names}{more}."[:300]
    url = search_url({**alert.filters, "sort": "recent"})
    Notification.objects.create(user=alert.user, kind="alert", title=title, body=body, url=url)
    sender = SENDERS.get(alert.channel)
    if sender and alert.channel != SavedSearch.Channel.IN_APP:
        try:
            sender.send(alert, title, body, url)
        except Exception:  # a failing e-mail must not stop the other alerts
            logger.exception("Alert delivery failed (alert %s)", alert.pk)


def run_alerts(now=None) -> dict:
    now = now or timezone.now()
    checked = notified = 0
    for alert in SavedSearch.objects.filter(is_active=True).select_related("user"):
        checked += 1
        matches = new_matches(alert)
        total = matches.count()
        if total:
            notify(alert, list(matches[:SHOWN]), total)
            notified += 1
        alert.last_notified_at = now
        alert.save(update_fields=["last_notified_at", "updated_at"])
    return {"alerts": checked, "notified": notified}
