import hashlib
import hmac
import json
import time
from datetime import timedelta

import httpx
import pytest
from django.core.management import call_command
from django.utils import timezone

from analytics.models import Event
from marketplace.models import Listing
from trust.tests import make_listing, make_seller

from . import services
from .models import Order, OrderEvent, Transaction
from .providers import base as provider_base
from .providers import get_provider
from .providers.fedapay import FedaPayProvider
from .services import InvalidTransition, OrderError

PAY_OK = "01 97 12 34 12"


@pytest.fixture
def catalog(db):
    call_command("seed_catalog", verbosity=0)


@pytest.fixture
def world(catalog):
    seller = make_seller(1)
    buyer = make_seller(2)
    listing = make_listing(seller, status="active", price_fcfa=185_000)
    return seller, buyer, listing


def paid_order(buyer, listing, phone=PAY_OK):
    order = services.create_order(buyer, listing)
    return services.start_payment(order, "mtn", phone)


def listing_status(listing):
    return Listing.objects.get(pk=listing.pk).status


def test_commission_is_3_percent_with_a_minimum(settings):
    assert services.commission_for(185_000) == 5_550
    assert services.commission_for(10_000) == 500  # 3 % would be 300
    assert services.commission_for(300) == 300  # never more than the price
    settings.ESCROW_COMMISSION_PCT = 5
    assert services.commission_for(185_000) == 9_250


def test_create_order_computes_the_split_and_logs_the_start(world):
    seller, buyer, listing = world
    order = services.create_order(buyer, listing, "delivery", "Livrez à Cotonou")
    assert (order.amount_fcfa, order.commission_fcfa, order.seller_payout_fcfa) == (
        185_000,
        5_550,
        179_450,
    )
    assert order.status == "created" and order.is_sandbox and order.seller == seller
    assert order.history.get().to_status == "created"
    assert Event.objects.filter(type="checkout_start", listing=listing, user=buyer).exists()
    assert services.create_order(buyer, listing).pk == order.pk  # reused, not duplicated


def test_create_order_rules(world):
    seller, buyer, listing = world
    with pytest.raises(OrderError, match="propre annonce"):
        services.create_order(seller, listing)
    Listing.objects.filter(pk=listing.pk).update(accepts_secure_payment=False)
    listing.refresh_from_db()
    with pytest.raises(OrderError, match="pas disponible"):
        services.create_order(buyer, listing)
    Listing.objects.filter(pk=listing.pk).update(accepts_secure_payment=True, status="sold")
    listing.refresh_from_db()
    with pytest.raises(OrderError):
        services.create_order(buyer, listing)


def test_a_listing_with_an_open_purchase_cannot_be_bought_again(world):
    seller, buyer, listing = world
    paid_order(buyer, listing)
    with pytest.raises(OrderError, match="déjà en cours"):
        services.create_order(make_seller(3), Listing.objects.get(pk=listing.pk))


def test_full_escrow_path_with_the_simulator(world):
    seller, buyer, listing = world
    order = paid_order(buyer, listing)
    assert order.status == "paid_held"
    assert listing_status(listing) == "reserved"
    tx = order.transactions.get(direction="in")
    assert tx.status == "succeeded" and tx.provider == "simulator" and tx.operator == "mtn"
    assert Event.objects.filter(type="order_paid", listing=listing).exists()

    order = services.mark_handed_over(order, seller)
    assert order.status == "handed_over"
    assert order.auto_release_at - order.handed_over_at == timedelta(hours=48)

    order = services.buyer_confirm(order, buyer)
    assert order.status == "released" and order.buyer_confirmed_at
    listing.refresh_from_db()
    assert listing.status == "sold" and listing.sold_at
    payout = order.transactions.get(direction="out")
    assert payout.amount_fcfa == 179_450 and payout.status == "succeeded"
    assert [e.to_status for e in order.history.all()] == [
        "created",
        "payment_pending",
        "paid_held",
        "handed_over",
        "released",
    ]


def test_failed_payment_cancels_the_order_and_frees_the_listing(world):
    _, buyer, listing = world
    order = paid_order(buyer, listing, "01 97 12 34 00")
    assert order.status == "cancelled"
    assert order.transactions.get().status == "failed"
    assert listing_status(listing) == "active"


def test_delayed_payment_settles_when_the_order_is_read_again(world):
    _, buyer, listing = world
    order = paid_order(buyer, listing, "01 97 12 34 77")
    assert order.status == "payment_pending" and listing_status(listing) == "active"
    tx = order.transactions.get()
    tx.raw_payload = {
        **tx.raw_payload,
        "settle_at": (timezone.now() - timedelta(seconds=1)).isoformat(),
    }
    tx.save()
    assert services.refresh_payment(order).status == "paid_held"


def test_invalid_transitions_are_refused(world):
    seller, buyer, listing = world
    order = services.create_order(buyer, listing)
    for action in (
        lambda: services.mark_handed_over(order, seller),
        lambda: services.buyer_confirm(order, buyer),
        lambda: services.release(order),
        lambda: services.mark_paid(order),
    ):
        with pytest.raises(InvalidTransition):
            action()
    order = services.start_payment(order, "moov", PAY_OK)
    with pytest.raises(InvalidTransition):
        services.buyer_confirm(order, buyer)  # the seller has not handed the device over
    with pytest.raises(InvalidTransition):
        services.cancel(order, buyer)  # paid: only a dispute can undo it


def test_only_the_right_party_can_act(world):
    seller, buyer, listing = world
    order = paid_order(buyer, listing)
    with pytest.raises(OrderError):
        services.mark_handed_over(order, buyer)
    order = services.mark_handed_over(order, seller)
    with pytest.raises(OrderError):
        services.buyer_confirm(order, seller)
    with pytest.raises(OrderError):
        services.open_dispute(order, seller, "Je veux un litige maintenant")
    with pytest.raises(OrderError):
        services.cancel(
            services.create_order(
                buyer, make_listing(seller, imei="35" + "5" * 13, status="active")
            ),
            seller,
        )


def test_cancelling_before_payment(world):
    _, buyer, listing = world
    order = services.cancel(services.create_order(buyer, listing), buyer)
    assert order.status == "cancelled" and listing_status(listing) == "active"


def test_a_dispute_needs_a_reason_and_stops_the_automatic_release(world):
    seller, buyer, listing = world
    order = services.mark_handed_over(paid_order(buyer, listing), seller)
    with pytest.raises(OrderError, match="10 caractères"):
        services.open_dispute(order, buyer, "court")
    order = services.open_dispute(order, buyer, "L'écran est fissuré, pas comme décrit")
    assert order.status == "disputed" and order.auto_release_at is None
    assert listing_status(listing) == "reserved"


def test_a_moderator_can_release_a_dispute_to_the_seller(world):
    seller, buyer, listing = world
    order = services.open_dispute(paid_order(buyer, listing), buyer, "L'appareil n'a pas été remis")
    order = services.resolve_dispute(order, make_seller(9), "release")
    assert order.status == "released" and listing_status(listing) == "sold"
    assert order.transactions.filter(direction="out").exists()


def test_a_moderator_can_refund_the_buyer(world):
    seller, buyer, listing = world
    order = services.open_dispute(paid_order(buyer, listing), buyer, "L'appareil n'a pas été remis")
    moderator = make_seller(9)
    order = services.resolve_dispute(order, moderator, "refund")
    assert order.status == "refunded" and listing_status(listing) == "active"
    refund = order.transactions.get(direction="refund")
    assert refund.amount_fcfa == 185_000 and refund.status == "succeeded"
    with pytest.raises(InvalidTransition):
        services.resolve_dispute(order, moderator, "release")  # decided once


def test_a_payment_for_a_listing_sold_meanwhile_is_refunded(world):
    _, buyer, listing = world
    order = services.create_order(buyer, listing)
    Listing.objects.filter(pk=listing.pk).update(status="sold")
    order = services.start_payment(order, "mtn", PAY_OK)
    assert order.status == "refunded"
    assert order.transactions.filter(direction="refund").exists()


def test_release_due_orders_releases_after_48_hours_and_expires_unpaid_orders(world, settings):
    seller, buyer, listing = world
    order = services.mark_handed_over(paid_order(buyer, listing), seller)
    assert services.release_due_orders()["released"] == 0  # not due yet
    Order.objects.filter(pk=order.pk).update(auto_release_at=timezone.now() - timedelta(minutes=1))
    assert services.release_due_orders()["released"] == 1
    assert Order.objects.get(pk=order.pk).status == "released"
    assert OrderEvent.objects.filter(order=order, note="Libération automatique").exists()

    other = make_listing(seller, imei="35" + "7" * 13, status="active")
    abandoned = services.create_order(buyer, other)
    Order.objects.filter(pk=abandoned.pk).update(
        created_at=timezone.now() - timedelta(minutes=settings.PAYMENT_PENDING_MINUTES + 1)
    )
    third = make_listing(seller, imei="35" + "8" * 13, status="active")
    stuck = services.start_payment(
        services.create_order(make_seller(4), third), "mtn", "01 97 12 34 99"
    )
    Order.objects.filter(pk=stuck.pk).update(
        payment_expires_at=timezone.now() - timedelta(minutes=1)
    )
    assert services.release_due_orders()["expired"] == 2
    assert Order.objects.get(pk=abandoned.pk).status == "cancelled"
    assert Order.objects.get(pk=stuck.pk).status == "cancelled"


def test_the_command_runs(world):
    call_command("release_due_orders")


# ------------------------------------------------------------------------------- API


def api(client, user, method, url, body=None, **headers):
    client.force_login(user)
    kwargs = {"content_type": "application/json", **headers}
    data = json.dumps(body) if body is not None else None
    return getattr(client, method)(url, data, **kwargs)


def test_api_buy_pay_hand_over_confirm(world, client):
    seller, buyer, listing = world
    r = api(
        client, buyer, "post", "/api/orders/", {"listing_id": listing.pk, "delivery_mode": "meetup"}
    )
    assert r.status_code == 201
    order = r.json()
    assert order["actions"]["pay"] and order["role"] == "buyer"
    assert order["commission_fcfa"] is None  # the commission is the seller's business
    url = f"/api/orders/{order['id']}"

    bad = api(client, buyer, "post", f"{url}/pay/", {"operator": "mtn", "phone": "12"})
    assert bad.status_code == 400 and "phone" in bad.json()["fields"]
    r = api(client, buyer, "post", f"{url}/pay/", {"operator": "mtn", "phone": PAY_OK})
    assert r.json()["status"] == "paid_held"

    seen = api(client, seller, "get", f"{url}/").json()
    assert seen["role"] == "seller" and seen["commission_fcfa"] == 5_550
    assert seen["actions"]["hand_over"] and not seen["actions"]["confirm"]
    assert api(client, buyer, "post", f"{url}/handed-over/").status_code == 400
    assert api(client, seller, "post", f"{url}/handed-over/").json()["status"] == "handed_over"
    assert api(client, seller, "post", f"{url}/confirm/").status_code == 400
    final = api(client, buyer, "post", f"{url}/confirm/").json()
    assert final["status"] == "released"
    assert [h["to"] for h in final["history"]][-1] == "released"

    mine = api(client, buyer, "get", "/api/me/orders/").json()
    assert [o["id"] for o in mine] == [order["id"]]


def test_api_strangers_cannot_see_an_order_and_replays_are_harmless(world, client):
    _, buyer, listing = world
    order = services.create_order(buyer, listing)
    assert api(client, make_seller(7), "get", f"/api/orders/{order.pk}/").status_code == 404
    pay = {"operator": "mtn", "phone": PAY_OK}
    first = api(
        client, buyer, "post", f"/api/orders/{order.pk}/pay/", pay, HTTP_IDEMPOTENCY_KEY="abc"
    )
    again = api(
        client, buyer, "post", f"/api/orders/{order.pk}/pay/", pay, HTTP_IDEMPOTENCY_KEY="abc"
    )
    assert first.status_code == again.status_code == 200
    assert Transaction.objects.filter(order=order, direction="in").count() == 1


def test_api_dispute_and_conflicts(world, client):
    seller, buyer, listing = world
    order = paid_order(buyer, listing)
    r = api(client, buyer, "post", f"/api/orders/{order.pk}/dispute/", {"reason": "court"})
    assert r.status_code == 400
    r = api(client, buyer, "post", f"/api/orders/{order.pk}/cancel/")
    assert r.status_code == 409  # already paid
    r = api(
        client,
        buyer,
        "post",
        f"/api/orders/{order.pk}/dispute/",
        {"reason": "Rien reçu de l'appareil"},
    )
    assert r.json()["status"] == "disputed"


def test_api_update_details_only_before_payment(world, client):
    _, buyer, listing = world
    order = services.create_order(buyer, listing)
    r = api(
        client,
        buyer,
        "patch",
        f"/api/orders/{order.pk}/",
        {"delivery_mode": "delivery", "meetup_note": "Akpakpa"},
    )
    assert r.json()["delivery_mode"] == "delivery"
    paid = services.start_payment(order, "mtn", PAY_OK)
    r = api(client, buyer, "patch", f"/api/orders/{paid.pk}/", {"delivery_mode": "meetup"})
    assert r.status_code == 400


def test_simulator_settle_endpoint_is_for_development_only(world, client, settings):
    _, buyer, listing = world
    order = paid_order(buyer, listing, "01 97 12 34 99")
    assert order.status == "payment_pending"
    settings.DEBUG = False
    assert (
        api(client, buyer, "post", f"/api/orders/{order.pk}/simulator-settle/").status_code == 404
    )
    settings.DEBUG = True
    assert (
        api(client, buyer, "post", f"/api/orders/{order.pk}/simulator-settle/").json()["status"]
        == "paid_held"
    )


def test_commission_endpoint(db, client):
    body = client.get("/api/payments/commission/?price=185000").json()
    assert (body["commission_fcfa"], body["payout_fcfa"]) == (5_550, 179_450)
    assert client.get("/api/payments/commission/").json()["commission_fcfa"] == 0


def test_the_secure_payment_filter(world, client):
    seller, _, listing = world
    off = make_listing(seller, imei="35" + "6" * 13, status="active", accepts_secure_payment=False)
    ids = {r["id"] for r in client.get("/api/listings/?secure_payment=1").json()["results"]}
    assert listing.pk in ids and off.pk not in ids


def test_the_admin_resolves_disputes(world, client):
    from accounts.models import User

    seller, buyer, listing = world
    order = services.open_dispute(
        paid_order(buyer, listing), buyer, "Appareil non conforme à l'annonce"
    )
    admin = User.objects.create_superuser("adm", "adm@example.com", "x-y-z-12345")
    client.force_login(admin)
    assert client.get("/admin/payments/order/").status_code == 200
    r = client.post(
        "/admin/payments/order/",
        {"action": "refund_buyer", "_selected_action": [order.pk]},
        follow=True,
    )
    assert r.status_code == 200
    assert Order.objects.get(pk=order.pk).status == "refunded"


# ------------------------------------------------------------------------------- FedaPay


SECRET = "whsec_test"


def sign(body: str, timestamp=None) -> str:
    t = str(timestamp or int(time.time()))
    digest = hmac.new(SECRET.encode(), f"{t}.{body}".encode(), hashlib.sha256).hexdigest()
    return f"t={t},s={digest}"


@pytest.fixture
def fedapay(settings, monkeypatch):
    settings.PAYMENT_PROVIDER = "fedapay"
    settings.FEDAPAY_SECRET_KEY = "sk_sandbox_x"
    settings.FEDAPAY_WEBHOOK_SECRET = SECRET
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, request.content))
        path = request.url.path
        if path.endswith("/token"):
            return httpx.Response(
                200, json={"token": "tok", "url": "https://sandbox-process.fedapay.com/tok"}
            )
        if path.endswith("/transactions"):
            return httpx.Response(200, json={"v1/transaction": {"id": 4242, "status": "pending"}})
        if path.endswith("/payouts"):
            return httpx.Response(200, json={"v1/payout": {"id": 77}})
        if path.endswith("/payouts/start"):
            return httpx.Response(200, json={"v1/payouts": [{"id": 77}]})
        return httpx.Response(404)

    monkeypatch.setattr(
        provider_base,
        "http_client",
        lambda timeout=15: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return calls


def webhook(client, name="transaction.approved", event_id="evt_1", signature=None, entity_id=4242):
    body = json.dumps(
        {"id": event_id, "name": name, "entity": {"v1/transaction": {"id": entity_id}}}
    )
    return client.post(
        "/api/payments/webhooks/fedapay/",
        body,
        content_type="application/json",
        HTTP_X_FEDAPAY_SIGNATURE=sign(body) if signature is None else signature,
    )


def test_fedapay_payment_waits_for_the_webhook(world, fedapay, client):
    _, buyer, listing = world
    order = paid_order(buyer, listing)
    assert order.status == "payment_pending"
    tx = order.transactions.get()
    assert tx.provider == "fedapay" and tx.provider_reference == "4242"
    assert tx.raw_payload["checkout_url"].startswith("https://sandbox-process.fedapay.com/")
    assert webhook(client).status_code == 204
    order.refresh_from_db()
    assert order.status == "paid_held" and listing_status(listing) == "reserved"


def test_webhooks_are_idempotent(world, fedapay, client):
    _, buyer, listing = world
    order = paid_order(buyer, listing)
    for _ in range(3):  # the provider retries
        assert webhook(client).status_code == 204
    order.refresh_from_db()
    assert order.status == "paid_held"
    assert Event.objects.filter(type="order_paid", listing=listing).count() == 1


def test_a_declined_webhook_cancels_the_order(world, fedapay, client):
    _, buyer, listing = world
    order = paid_order(buyer, listing)
    assert webhook(client, "transaction.declined", "evt_2").status_code == 204
    order.refresh_from_db()
    assert order.status == "cancelled" and listing_status(listing) == "active"


def test_webhook_signature_is_verified(world, fedapay, client):
    _, buyer, listing = world
    order = paid_order(buyer, listing)
    assert webhook(client, signature="t=1,s=deadbeef").status_code == 401
    assert webhook(client, signature="").status_code == 401
    old = sign("{}", timestamp=int(time.time()) - 3600)
    body = json.dumps({"id": "e", "name": "transaction.approved", "entity": {"id": 4242}})
    stale = client.post(
        "/api/payments/webhooks/fedapay/",
        body,
        content_type="application/json",
        HTTP_X_FEDAPAY_SIGNATURE=sign(body, int(time.time()) - 3600),
    )
    assert stale.status_code == 401 and old
    order.refresh_from_db()
    assert order.status == "payment_pending"  # nothing was applied


def test_fedapay_payout_and_unknown_events(world, fedapay, client):
    seller, buyer, listing = world
    order = paid_order(buyer, listing)
    webhook(client)
    order = services.mark_handed_over(Order.objects.get(pk=order.pk), seller)
    order = services.buyer_confirm(order, buyer)
    assert order.transactions.get(direction="out").provider_reference == "77"
    assert any(path.endswith("/payouts/start") for _, path, _ in fedapay)
    body = json.dumps({"id": "x", "name": "customer.created", "entity": {}})
    r = client.post(
        "/api/payments/webhooks/fedapay/",
        body,
        content_type="application/json",
        HTTP_X_FEDAPAY_SIGNATURE=sign(body),
    )
    assert r.status_code == 204


def test_provider_outage_fails_the_payment_cleanly(world, settings, monkeypatch):
    settings.PAYMENT_PROVIDER = "fedapay"
    settings.FEDAPAY_SECRET_KEY = "sk"
    monkeypatch.setattr(
        provider_base,
        "http_client",
        lambda timeout=15: httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(503))
        ),
    )
    _, buyer, listing = world
    order = paid_order(buyer, listing)
    assert order.status == "cancelled" and listing_status(listing) == "active"


def test_the_default_provider_is_the_simulator(db):
    assert get_provider().name == "simulator"
    assert isinstance(get_provider("fedapay"), FedaPayProvider)
