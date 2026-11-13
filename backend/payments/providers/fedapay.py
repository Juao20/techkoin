"""FedaPay, sandbox environment (spec 3.4).

The buyer is redirected to FedaPay's checkout page; the result reaches us by webhook (and by
polling when the buyer comes back). Written from FedaPay's public documentation and not yet
run against the sandbox with real keys: see docs/DECISIONS.md.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import httpx
from django.conf import settings

from . import base
from .base import InvalidSignature, PaymentProvider, ProviderError, ProviderResult, WebhookEvent

URLS = {
    "sandbox": "https://sandbox-api.fedapay.com/v1",
    "live": "https://api.fedapay.com/v1",
}
SIGNATURE_TOLERANCE_SECONDS = 300
APPROVED = {"approved", "transferred"}
FAILED = {"declined", "canceled", "cancelled", "refunded"}
OPERATOR_MODES = {"mtn": "mtn_open", "moov": "moov", "celtiis": "celtiis_bj"}


def _digits(phone: str) -> str:
    return "".join(c for c in phone if c.isdigit()).removeprefix("229")


def _status(value: str) -> str:
    if value in APPROVED:
        return "succeeded"
    if value in FAILED:
        return "failed"
    return "pending"


def _entity(body: dict) -> dict:
    """FedaPay wraps entities as {"v1/transaction": {...}}."""
    for key, value in body.items():
        if key.startswith("v1/") and isinstance(value, dict):
            return value
    return body


class FedaPayProvider(PaymentProvider):
    name = "fedapay"

    @property
    def api(self) -> str:
        return URLS["live" if settings.FEDAPAY_ENV == "live" else "sandbox"]

    def _request(self, method: str, path: str, **kwargs) -> dict:
        if not settings.FEDAPAY_SECRET_KEY:
            raise ProviderError("FEDAPAY_SECRET_KEY manquante.")
        try:
            with base.http_client() as client:
                response = client.request(
                    method,
                    f"{self.api}{path}",
                    headers={"Authorization": f"Bearer {settings.FEDAPAY_SECRET_KEY}"},
                    **kwargs,
                )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"FedaPay : {type(exc).__name__}") from exc

    def initiate(self, order, operator, phone, idempotency_key):
        created = _entity(
            self._request(
                "POST",
                "/transactions",
                json={
                    "description": getattr(
                        order, "provider_description", f"Commande TechKoin {order.pk}"
                    ),
                    "amount": order.amount_fcfa,
                    "currency": {"iso": "XOF"},
                    "callback_url": settings.SITE_URL
                    + getattr(order, "callback_path", f"/commande/{order.pk}"),
                    "custom_metadata": {
                        ("subscription_id" if hasattr(order, "shop") else "order_id"): order.pk,
                        "operator": operator,
                    },
                    "customer": {"phone_number": {"number": _digits(phone), "country": "bj"}},
                },
            )
        )
        reference = str(created["id"])
        token = self._request("POST", f"/transactions/{reference}/token")
        return ProviderResult(
            "pending", reference, {"transaction": created}, checkout_url=token.get("url", "")
        )

    def poll(self, transaction):
        data = _entity(self._request("GET", f"/transactions/{transaction.provider_reference}"))
        status = _status(str(data.get("status", "")))
        if status == "pending":
            return None
        return ProviderResult(status, transaction.provider_reference, {"transaction": data})

    def _send(self, order, phone, operator, key, label):
        payout = _entity(
            self._request(
                "POST",
                "/payouts",
                json={
                    "amount": order.seller_payout_fcfa if label == "out" else order.amount_fcfa,
                    "currency": {"iso": "XOF"},
                    "mode": OPERATOR_MODES.get(operator, "mtn_open"),
                    "customer": {"phone_number": {"number": _digits(phone), "country": "bj"}},
                    "custom_metadata": {"order_id": order.pk, "kind": label, "key": key},
                },
            )
        )
        reference = str(payout["id"])
        self._request("PUT", "/payouts/start", json={"payouts": [{"id": payout["id"]}]})
        return ProviderResult("succeeded", reference, {"payout": payout})

    def payout(self, order, phone, idempotency_key):
        return self._send(order, phone, "mtn", idempotency_key, "out")

    def refund(self, order, phone, idempotency_key):
        return self._send(order, phone, "mtn", idempotency_key, "refund")

    def parse_webhook(self, headers, body: bytes):
        """Header `X-FEDAPAY-SIGNATURE: t=<unix time>,s=<hex HMAC-SHA256 of "t.body">`."""
        secret = settings.FEDAPAY_WEBHOOK_SECRET
        header = headers.get("X-FEDAPAY-SIGNATURE") or headers.get("X-Fedapay-Signature") or ""
        parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
        if not secret or "t" not in parts or "s" not in parts:
            raise InvalidSignature("signature absente")
        expected = hmac.new(
            secret.encode(), f"{parts['t']}.{body.decode()}".encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, parts["s"]):
            raise InvalidSignature("signature invalide")
        try:
            if abs(time.time() - int(parts["t"])) > SIGNATURE_TOLERANCE_SECONDS:
                raise InvalidSignature("horodatage trop ancien")
        except ValueError as exc:
            raise InvalidSignature("horodatage invalide") from exc
        payload = json.loads(body)
        name = str(payload.get("name", ""))
        if not name.startswith("transaction."):
            return None
        entity = _entity(payload.get("entity") or {})
        status = _status(name.split(".", 1)[1])
        if status == "pending":
            return None
        return WebhookEvent(
            event_id=str(payload.get("id") or f"{name}:{entity.get('id')}"),
            reference=str(entity.get("id", "")),
            status=status,
            raw=payload,
        )
