"""Pro plan subscription (spec 9.3): a Transaction of direction `in`, no escrow.

The plan switches to `pro` the moment the sandbox payment succeeds. Paying again while Pro
extends the current period by one month instead of overlapping it.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import Shop

from .models import Subscription, Transaction
from .providers import get_provider
from .providers.base import ProviderError, ProviderResult
from .services import OPERATORS, OrderError

PERIOD = timedelta(days=30)


def latest(shop: Shop) -> Subscription | None:
    return shop.subscriptions.first()


def start(shop: Shop, operator: str, phone: str, key: str | None = None) -> Subscription:
    if operator not in OPERATORS:
        raise OrderError("Choisissez un opérateur.")
    if shop.subscriptions.filter(status=Subscription.Status.PENDING).exists():
        raise OrderError("Un paiement d'abonnement est déjà en cours.")
    provider = get_provider()
    key = key or f"sub-{shop.pk}-{uuid.uuid4().hex[:10]}"
    sub = Subscription.objects.create(shop=shop, amount_fcfa=settings.PRO_PLAN_PRICE_FCFA)
    try:
        result = provider.initiate(sub, operator, phone, key)
    except ProviderError as exc:
        result = ProviderResult("failed", "", {"error": str(exc)}, message=str(exc))
    with transaction.atomic():
        tx = Transaction.objects.create(
            subscription=sub,
            provider=provider.name,
            operator=operator,
            payer_phone=phone,
            amount_fcfa=sub.amount_fcfa,
            direction="in",
            provider_reference=result.reference,
            status=Transaction.Status.PENDING,
            raw_payload={
                **result.raw,
                **({"checkout_url": result.checkout_url} if result.checkout_url else {}),
            },
            idempotency_key=key,
        )
        apply_result(sub, tx, result)
    sub.refresh_from_db()
    return sub


def apply_result(sub: Subscription, tx: Transaction, result: ProviderResult) -> None:
    """Idempotent: a transaction that already ended is left alone."""
    if tx.status != Transaction.Status.PENDING:
        return
    tx.status = result.status
    tx.raw_payload = {**tx.raw_payload, **result.raw}
    tx.save(update_fields=["status", "raw_payload", "updated_at"])
    if result.status == "succeeded":
        activate(sub)
    elif result.status == "failed":
        sub.status = Subscription.Status.FAILED
        sub.save(update_fields=["status", "updated_at"])


@transaction.atomic
def activate(sub: Subscription) -> None:
    shop = Shop.objects.select_for_update().get(pk=sub.shop_id)
    now = timezone.now()
    start = shop.plan_expires_at if shop.is_pro and shop.plan_expires_at else now
    sub.status = Subscription.Status.ACTIVE
    sub.starts_at, sub.ends_at = start, start + PERIOD
    sub.save(update_fields=["status", "starts_at", "ends_at", "updated_at"])
    shop.plan, shop.plan_expires_at = Shop.Plan.PRO, sub.ends_at
    shop.save(update_fields=["plan", "plan_expires_at", "updated_at"])


def refresh(sub: Subscription) -> Subscription:
    """Poll the provider for a pending subscription payment (delayed simulator, FedaPay)."""
    if sub.status != Subscription.Status.PENDING:
        return sub
    provider = get_provider()
    for tx in sub.transactions.filter(direction="in", status="pending"):
        try:
            result = provider.poll(tx)
        except ProviderError:
            continue
        if result:
            with transaction.atomic():
                apply_result(sub, Transaction.objects.select_for_update().get(pk=tx.pk), result)
    sub.refresh_from_db()
    return sub


def refresh_pending(shop: Shop) -> None:
    for sub in shop.subscriptions.filter(status=Subscription.Status.PENDING):
        refresh(sub)
    shop.refresh_from_db()


def expire_due(now=None) -> int:
    """Back to the free plan once the paid period is over. Run by `release_due_orders`."""
    now = now or timezone.now()
    count = 0
    for shop in Shop.objects.filter(plan=Shop.Plan.PRO, plan_expires_at__lte=now):
        shop.plan = Shop.Plan.FREE
        shop.save(update_fields=["plan", "updated_at"])
        shop.subscriptions.filter(status=Subscription.Status.ACTIVE).update(
            status=Subscription.Status.EXPIRED
        )
        count += 1
    return count
