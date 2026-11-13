"""Local Mobile Money simulation: no network, no money.

The last two digits of the phone number choose the outcome, so every path can be tried:
  ...00  the payment fails (insufficient funds)
  ...77  the payment succeeds after 5 seconds (checked when the order is read)
  ...99  the payment stays pending until it is settled by hand (admin or API in development)
  other  the payment succeeds at once
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.utils import timezone

from .base import PaymentProvider, ProviderResult

DELAY_SECONDS = 5


class SimulatorProvider(PaymentProvider):
    name = "simulator"

    def initiate(self, order, operator, phone, idempotency_key):
        ref = f"SIM-{uuid.uuid4().hex[:12].upper()}"
        ending = phone[-2:]
        if ending == "00":
            return ProviderResult(
                "failed", ref, {"simulated": "failed"}, message="Solde insuffisant (simulation)"
            )
        if ending == "77":
            due = (timezone.now() + timedelta(seconds=DELAY_SECONDS)).isoformat()
            return ProviderResult("pending", ref, {"simulated": "delayed", "settle_at": due})
        if ending == "99":
            return ProviderResult("pending", ref, {"simulated": "manual"})
        return ProviderResult("succeeded", ref, {"simulated": "succeeded"})

    def poll(self, transaction):
        raw = transaction.raw_payload or {}
        if raw.get("simulated") == "delayed" and raw.get("settle_at"):
            if timezone.now().isoformat() >= raw["settle_at"]:
                return ProviderResult("succeeded", transaction.provider_reference, raw)
        if raw.get("settled"):
            return ProviderResult("succeeded", transaction.provider_reference, raw)
        return None

    def payout(self, order, phone, idempotency_key):
        return ProviderResult("succeeded", f"SIM-OUT-{uuid.uuid4().hex[:10].upper()}")

    def refund(self, order, phone, idempotency_key):
        return ProviderResult("succeeded", f"SIM-REF-{uuid.uuid4().hex[:10].upper()}")
