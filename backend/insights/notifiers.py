"""Channels a report can leave through. E-mail now; WhatsApp later needs only a new class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from django.conf import settings
from django.core.mail import send_mail


class Notifier(ABC):
    name: str

    @abstractmethod
    def send(self, shop, subject: str, body: str) -> bool:
        """Deliver the message to the shop owner. Return True when it left."""


class EmailNotifier(Notifier):
    name = "email"

    def send(self, shop, subject: str, body: str) -> bool:
        address = shop.owner.email
        if not address:
            return False
        return bool(
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [address], fail_silently=False)
        )


NOTIFIERS: list[Notifier] = [EmailNotifier()]
