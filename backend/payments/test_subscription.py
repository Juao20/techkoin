from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Shop, User
from payments import subscriptions
from payments.models import Subscription

pytestmark = pytest.mark.django_db


def make_shop(n=1, plan="free"):
    owner = User.objects.create_user(
        username=f"shop{n}", email=f"shop{n}@t.test", password="x", account_type="boutique"
    )
    return Shop.objects.create(owner=owner, name=f"Boutique {n}", slug=f"boutique-{n}", plan=plan)


def client_for(shop):
    c = APIClient()
    c.force_login(shop.owner)
    return c


def test_payment_switches_the_shop_to_pro_at_once():
    shop = make_shop()
    r = client_for(shop).post(
        "/api/shop/subscribe/", {"operator": "mtn", "phone": "01 97 12 34 56"}, format="json"
    )
    assert r.status_code == 201
    assert r.json()["plan"] == "pro"
    shop.refresh_from_db()
    assert shop.is_pro
    assert shop.plan_expires_at > timezone.now() + timedelta(days=29)
    sub = shop.subscriptions.get()
    assert sub.status == "active"
    tx = sub.transactions.get()
    assert (tx.direction, tx.status, tx.amount_fcfa) == ("in", "succeeded", 10_000)


def test_refused_payment_keeps_the_free_plan():
    shop = make_shop()
    r = client_for(shop).post(
        "/api/shop/subscribe/", {"operator": "moov", "phone": "01 97 12 34 00"}, format="json"
    )
    assert r.status_code == 201
    shop.refresh_from_db()
    assert not shop.is_pro
    assert shop.subscriptions.get().status == "failed"


def test_pending_payment_is_settled_later():
    shop = make_shop()
    c = client_for(shop)
    c.post("/api/shop/subscribe/", {"operator": "mtn", "phone": "01 97 12 34 99"}, format="json")
    shop.refresh_from_db()
    assert not shop.is_pro
    assert (
        c.post("/api/shop/subscribe/", {"operator": "mtn", "phone": "0197123456"}).status_code
        == 400
    )
    sub = shop.subscriptions.get()
    tx = sub.transactions.get()
    tx.raw_payload = {**tx.raw_payload, "settled": True}
    tx.save()
    assert c.get("/api/shop/subscription/").json()["plan"] == "pro"


def test_paying_again_extends_the_period():
    shop = make_shop()
    c = client_for(shop)
    for _ in range(2):
        c.post(
            "/api/shop/subscribe/", {"operator": "mtn", "phone": "01 97 12 34 56"}, format="json"
        )
    shop.refresh_from_db()
    assert shop.plan_expires_at > timezone.now() + timedelta(days=59)


def test_plan_ends_when_the_period_is_over():
    shop = make_shop(plan="pro")
    shop.plan_expires_at = timezone.now() - timedelta(minutes=1)
    shop.save()
    assert not shop.is_pro
    assert subscriptions.expire_due() == 1
    shop.refresh_from_db()
    assert shop.plan == "free"


def test_a_plan_without_expiry_is_granted_by_hand():
    assert make_shop(plan="pro").is_pro


def test_individual_accounts_cannot_subscribe():
    user = User.objects.create_user(username="p", email="p@t.test", password="x")
    c = APIClient()
    c.force_login(user)
    r = c.post("/api/shop/subscribe/", {"operator": "mtn", "phone": "0197123456"}, format="json")
    assert r.status_code == 403
    assert Subscription.objects.count() == 0


def test_invalid_phone_and_operator_are_refused():
    shop = make_shop()
    c = client_for(shop)
    assert c.post("/api/shop/subscribe/", {"operator": "mtn", "phone": "12"}).status_code == 400
    r = c.post("/api/shop/subscribe/", {"operator": "x", "phone": "0197123456"})
    assert r.status_code == 400
