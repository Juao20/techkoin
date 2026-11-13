"""The interface every payment provider implements (spec 3.4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx


class ProviderError(Exception):
    """The provider could not be reached or refused the request."""


class InvalidSignature(Exception):
    """A webhook did not carry a valid signature."""


@dataclass
class ProviderResult:
    status: str  # "pending" | "succeeded" | "failed"
    reference: str = ""
    raw: dict = field(default_factory=dict)
    checkout_url: str = ""
    message: str = ""


@dataclass
class WebhookEvent:
    event_id: str
    reference: str
    status: str  # "succeeded" | "failed"
    raw: dict = field(default_factory=dict)


def http_client(timeout: float = 15) -> httpx.Client:
    """Overridable in tests."""
    return httpx.Client(timeout=timeout)


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def initiate(self, order, operator: str, phone: str, idempotency_key: str) -> ProviderResult:
        """Start collecting the buyer's payment."""

    @abstractmethod
    def poll(self, transaction) -> ProviderResult | None:
        """Ask the provider where a pending transaction stands (None: nothing new)."""

    @abstractmethod
    def payout(self, order, phone: str, idempotency_key: str) -> ProviderResult:
        """Pay the seller once the buyer confirmed."""

    @abstractmethod
    def refund(self, order, phone: str, idempotency_key: str) -> ProviderResult:
        """Give the money back to the buyer."""

    def parse_webhook(self, headers, body: bytes) -> WebhookEvent | None:
        """Verify and decode a webhook. Providers without webhooks return None."""
        return None
