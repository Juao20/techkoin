"""Order state machine and escrow rules (spec 9.2).

Every transition is a dedicated function that runs in `transaction.atomic()`, checks the state
it starts from (an invalid one raises InvalidTransition), writes a history row, and moves the
listing along: paid_held reserves it, released sells it, cancelled or refunded frees it.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from analytics.models import Event
from analytics.tracking import record
from marketplace.models import Listing

from .models import Order, OrderEvent, Transaction
from .providers import get_provider
from .providers.base import ProviderError, ProviderResult

S = Order.Status

ALLOWED: dict[str, set[str]] = {
    S.CREATED: {S.PAYMENT_PENDING, S.CANCELLED},
    S.PAYMENT_PENDING: {S.PAID_HELD, S.CANCELLED, S.REFUNDED},
    S.PAID_HELD: {S.HANDED_OVER, S.DISPUTED},
    S.HANDED_OVER: {S.RELEASED, S.DISPUTED},
    S.DISPUTED: {S.RELEASED, S.REFUNDED},
    S.RELEASED: set(),
    S.REFUNDED: set(),
    S.CANCELLED: set(),
}
OPEN_STATUSES = (S.PAYMENT_PENDING, S.PAID_HELD, S.HANDED_OVER, S.DISPUTED)
OPERATORS = {o.value for o in Transaction.Operator}


class OrderError(Exception):
    """A business rule refused the action; the message is shown to the user in French."""


class InvalidTransition(OrderError):
    pass


def commission_for(amount_fcfa: int) -> int:
    """3 % by default, never below 500 FCFA, paid by the seller."""
    pct = round(amount_fcfa * settings.ESCROW_COMMISSION_PCT / 100)
    return min(amount_fcfa, max(pct, settings.ESCROW_COMMISSION_MIN_FCFA))


def _move(order: Order, to: str, actor=None, note: str = "") -> None:
    if to not in ALLOWED[order.status]:
        raise InvalidTransition(
            f"Cette action n'est pas possible pour une commande « {order.get_status_display()} »."
        )
    previous = order.status
    order.status = to
    order.save()
    OrderEvent.objects.create(
        order=order, from_status=previous, to_status=to, actor=actor, note=note[:300]
    )


def _set_listing(order: Order, status: str, **extra) -> None:
    Listing.objects.filter(pk=order.listing_id).update(status=status, **extra)


def _seller_phone(order: Order) -> str:
    seller = order.seller
    shop = getattr(seller, "shop", None)
    return (shop.whatsapp_number if shop else "") or seller.whatsapp_number or seller.phone or ""


def _buyer_phone(order: Order) -> str:
    paid = order.transactions.filter(direction="in", status="succeeded").first()
    return (paid.payer_phone if paid else "") or order.buyer.phone or ""


def _transaction(order, provider, direction, amount, key, result: ProviderResult, **extra):
    return Transaction.objects.create(
        order=order,
        provider=provider.name,
        direction=direction,
        amount_fcfa=amount,
        idempotency_key=key,
        provider_reference=result.reference,
        status=result.status,
        raw_payload=result.raw,
        **extra,
    )


# --------------------------------------------------------------------------- creation


@transaction.atomic
def create_order(buyer, listing: Listing, delivery_mode="meetup", meetup_note="") -> Order:
    if listing.seller_id == buyer.id:
        raise OrderError("Vous ne pouvez pas acheter votre propre annonce.")
    if Order.objects.filter(listing=listing, status__in=OPEN_STATUSES).exists():
        raise OrderError("Cette annonce est déjà en cours d'achat.")
    if listing.status != Listing.Status.ACTIVE or not listing.accepts_secure_payment:
        raise OrderError("Le paiement sécurisé n'est pas disponible pour cette annonce.")
    existing = Order.objects.filter(listing=listing, buyer=buyer, status=S.CREATED).first()
    if existing:
        return existing
    if delivery_mode not in Order.Delivery.values:
        raise OrderError("Choisissez le mode de remise.")
    amount = listing.price_fcfa
    commission = commission_for(amount)
    order = Order.objects.create(
        buyer=buyer,
        seller=listing.seller,
        listing=listing,
        amount_fcfa=amount,
        commission_fcfa=commission,
        seller_payout_fcfa=amount - commission,
        delivery_mode=delivery_mode,
        meetup_note=meetup_note[:300],
        is_sandbox=True,
    )
    OrderEvent.objects.create(order=order, to_status=S.CREATED, actor=buyer, note="Commande créée")
    record(Event.Type.CHECKOUT_START, user=buyer, listing=listing, metadata={"order": order.pk})
    return order


@transaction.atomic
def update_details(order: Order, buyer, delivery_mode: str, meetup_note: str) -> Order:
    if order.status != S.CREATED:
        raise OrderError("La commande ne peut plus être modifiée.")
    if delivery_mode not in Order.Delivery.values:
        raise OrderError("Choisissez le mode de remise.")
    order.delivery_mode, order.meetup_note = delivery_mode, meetup_note[:300]
    order.save()
    return order


# --------------------------------------------------------------------------- payment


def start_payment(order: Order, operator: str, phone: str, key: str | None = None) -> Order:
    """Ask the provider to collect the payment. The money goes to escrow, not to the seller."""
    if operator not in OPERATORS:
        raise OrderError("Choisissez un opérateur.")
    provider = get_provider()
    key = key or f"pay-{order.pk}-{uuid.uuid4().hex[:10]}"
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if Transaction.objects.filter(idempotency_key=key).exists():  # a repeated request
            return order
        _move(order, S.PAYMENT_PENDING, actor=order.buyer, note="Paiement initié")
        order.payment_expires_at = timezone.now() + timedelta(
            minutes=settings.PAYMENT_PENDING_MINUTES
        )
        order.save()
    try:
        result = provider.initiate(order, operator, phone, key)
    except ProviderError as exc:
        result = ProviderResult("failed", "", {"error": str(exc)}, message=str(exc))
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        tx = _transaction(
            order,
            provider,
            "in",
            order.amount_fcfa,
            key,
            ProviderResult("pending", result.reference, result.raw),  # applied just below
            operator=operator,
            payer_phone=phone,
        )
        if result.checkout_url:
            tx.raw_payload = {**tx.raw_payload, "checkout_url": result.checkout_url}
            tx.save(update_fields=["raw_payload", "updated_at"])
        _apply_result(order, tx, result)
    return Order.objects.get(pk=order.pk)


def _apply_result(order: Order, tx: Transaction, result: ProviderResult) -> None:
    """Apply a provider answer for an incoming payment. Idempotent: a final transaction stays."""
    if tx.status in (Transaction.Status.SUCCEEDED, Transaction.Status.FAILED):
        return
    tx.status = result.status
    tx.raw_payload = {**tx.raw_payload, **result.raw}
    tx.save(update_fields=["status", "raw_payload", "updated_at"])
    if result.status == "succeeded":
        mark_paid(order)
    elif result.status == "failed" and order.status == S.PAYMENT_PENDING:
        _move(order, S.CANCELLED, note=result.message or "Paiement refusé")


@transaction.atomic
def mark_paid(order: Order) -> Order:
    if order.status != S.PAYMENT_PENDING:
        raise InvalidTransition("Cette commande n'attend pas de paiement.")
    listing = Listing.objects.select_for_update().get(pk=order.listing_id)
    if listing.status != Listing.Status.ACTIVE:
        # Paid for something that is no longer for sale: give the money back at once.
        _move(order, S.REFUNDED, note="Annonce indisponible : remboursement")
        _refund_money(order)
        return order
    _move(order, S.PAID_HELD, note="Fonds placés en séquestre")
    _set_listing(order, Listing.Status.RESERVED)
    record(Event.Type.ORDER_PAID, user=order.buyer, listing=listing, metadata={"order": order.pk})
    return order


def refresh_payment(order: Order) -> Order:
    """Poll the provider for a pending payment (the buyer comes back, or the page refreshes)."""
    if order.status != S.PAYMENT_PENDING:
        return order
    provider = get_provider()
    for tx in order.transactions.filter(direction="in", status="pending"):
        try:
            result = provider.poll(tx)
        except ProviderError:
            continue
        if result:
            with transaction.atomic():
                fresh = Order.objects.select_for_update().get(pk=order.pk)
                _apply_result(fresh, Transaction.objects.get(pk=tx.pk), result)
    return Order.objects.get(pk=order.pk)


def handle_webhook(event) -> bool:
    """Apply a verified webhook once. Returns False when it was already processed."""
    key = f"webhook:{get_provider().name}:{event.event_id}"
    with transaction.atomic():
        if Transaction.objects.filter(idempotency_key=key).exists():
            return False
        tx = Transaction.objects.filter(provider_reference=event.reference, direction="in").first()
        if tx is None:
            return False
        # The webhook itself is remembered through a marker row carrying the idempotency key.
        Transaction.objects.create(
            order=tx.order,
            subscription=tx.subscription,
            provider=tx.provider,
            direction="in",
            amount_fcfa=0,
            status=Transaction.Status.SUCCEEDED if event.status == "succeeded" else "failed",
            provider_reference=event.reference,
            raw_payload=event.raw,
            idempotency_key=key,
        )
        result = ProviderResult(event.status, event.reference, event.raw)
        if tx.subscription_id:
            from . import subscriptions

            subscriptions.apply_result(tx.subscription, tx, result)
            return True
        order = Order.objects.select_for_update().get(pk=tx.order_id)
        _apply_result(order, tx, result)
    return True


@transaction.atomic
def cancel(order: Order, actor, note="Annulée par l'acheteur") -> Order:
    if actor.id != order.buyer_id:
        raise OrderError("Seul l'acheteur peut annuler la commande.")
    _move(order, S.CANCELLED, actor=actor, note=note)
    return order


# --------------------------------------------------------------------------- handover and release


@transaction.atomic
def mark_handed_over(order: Order, actor) -> Order:
    if actor.id != order.seller_id:
        raise OrderError("Seul le vendeur peut signaler la remise de l'appareil.")
    _move(order, S.HANDED_OVER, actor=actor, note="Remise signalée par le vendeur")
    now = timezone.now()
    order.handed_over_at = now
    order.auto_release_at = now + timedelta(hours=settings.ESCROW_AUTO_RELEASE_HOURS)
    order.save()
    return order


def _payout(order: Order) -> None:
    provider = get_provider()
    key = f"payout-{order.pk}"
    if Transaction.objects.filter(idempotency_key=key).exists():
        return
    try:
        result = provider.payout(order, _seller_phone(order), key)
    except ProviderError as exc:
        result = ProviderResult("failed", "", {"error": str(exc)})
    _transaction(order, provider, "out", order.seller_payout_fcfa, key, result)
    if result.status == "failed":
        raise OrderError("Le versement au vendeur a échoué. Un modérateur va le reprendre.")


@transaction.atomic
def release(order: Order, actor=None, note="Fonds versés au vendeur") -> Order:
    _move(order, S.RELEASED, actor=actor, note=note)
    _payout(order)
    _set_listing(order, Listing.Status.SOLD, sold_at=timezone.now())
    return order


@transaction.atomic
def buyer_confirm(order: Order, actor) -> Order:
    if actor.id != order.buyer_id:
        raise OrderError("Seul l'acheteur peut confirmer la réception.")
    if order.status != S.HANDED_OVER:
        raise InvalidTransition("Le vendeur n'a pas encore signalé la remise de l'appareil.")
    order.buyer_confirmed_at = timezone.now()
    return release(order, actor=actor, note="Réception confirmée par l'acheteur")


# --------------------------------------------------------------------------- disputes and refunds


@transaction.atomic
def open_dispute(order: Order, actor, reason: str) -> Order:
    if actor.id != order.buyer_id:
        raise OrderError("Seul l'acheteur peut ouvrir un litige.")
    reason = " ".join(reason.split())
    if len(reason) < 10:
        raise OrderError("Décrivez le problème en quelques mots (10 caractères au moins).")
    _move(order, S.DISPUTED, actor=actor, note="Litige ouvert")
    order.dispute_reason = reason[:1000]
    order.auto_release_at = None  # a dispute stops the automatic release
    order.save()
    return order


def _refund_money(order: Order) -> None:
    provider = get_provider()
    key = f"refund-{order.pk}"
    if Transaction.objects.filter(idempotency_key=key).exists():
        return
    try:
        result = provider.refund(order, _buyer_phone(order), key)
    except ProviderError as exc:
        result = ProviderResult("failed", "", {"error": str(exc)})
    _transaction(order, provider, "refund", order.amount_fcfa, key, result)
    if order.listing.status == Listing.Status.RESERVED:
        _set_listing(order, Listing.Status.ACTIVE)


@transaction.atomic
def resolve_dispute(order: Order, moderator, outcome: str, note: str = "") -> Order:
    if outcome == "release":
        return release(
            order, actor=moderator, note=note or "Litige tranché : fonds versés au vendeur"
        )
    if outcome == "refund":
        _move(
            order, S.REFUNDED, actor=moderator, note=note or "Litige tranché : acheteur remboursé"
        )
        _refund_money(order)
        return order
    raise OrderError("Décision inconnue.")


# --------------------------------------------------------------------------- scheduled work


def release_due_orders(now=None) -> dict[str, int]:
    """Run every 15 minutes: automatic release after 48 h, and expiry of unpaid orders."""
    now = now or timezone.now()
    released = expired = 0
    for order in Order.objects.filter(status=S.HANDED_OVER, auto_release_at__lte=now):
        try:
            with transaction.atomic():
                release(
                    Order.objects.select_for_update().get(pk=order.pk),
                    note="Libération automatique",
                )
            released += 1
        except OrderError:
            continue
    limit = now - timedelta(minutes=settings.PAYMENT_PENDING_MINUTES)
    stale = Order.objects.filter(status=S.CREATED, created_at__lte=limit) | Order.objects.filter(
        status=S.PAYMENT_PENDING, payment_expires_at__lte=now
    )
    for order in stale:
        refreshed = refresh_payment(order)  # a late success must not be lost
        if refreshed.status in (S.CREATED, S.PAYMENT_PENDING):
            with transaction.atomic():
                _move(
                    Order.objects.select_for_update().get(pk=order.pk),
                    S.CANCELLED,
                    note="Délai de paiement dépassé",
                )
            expired += 1
    return {"released": released, "expired": expired}
