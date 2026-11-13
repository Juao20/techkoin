from datetime import timedelta

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from insights.factories import add_listing, make_shop

from . import alerts
from .models import Notification, SavedSearch

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def catalog():
    call_command("seed_catalog", verbosity=0)


@pytest.fixture
def buyer():
    return User.objects.create_user(username="b", email="b@t.test", password="x-y-z-12345")


def login(user):
    c = APIClient()
    c.force_login(user)
    return c


def listing_after(alert, shop, slug="apple-iphone-13", **kw):
    """A listing published after the alert was created."""
    return add_listing(
        shop, slug, days_online=0, published_at=timezone.now() + timedelta(minutes=1), **kw
    )


def test_creating_an_alert_cleans_the_filters(buyer):
    r = login(buyer).post(
        "/api/me/alerts/",
        {"filters": {"q": "iphone 13", "price_max": 300000, "page": 4, "sort": "recent", "x": "y"}},
        format="json",
    )
    assert r.status_code == 201
    body = r.json()
    assert body["filters"] == {"q": "iphone 13", "price_max": "300000"}
    assert "iphone 13" in body["name"] and "300 000" in body["name"]
    assert body["channel"] == "email" and body["url"].startswith("/recherche?")


def test_an_alert_needs_criteria_and_is_limited(buyer):
    c = login(buyer)
    assert (
        c.post("/api/me/alerts/", {"filters": {"sort": "recent"}}, format="json").status_code == 400
    )
    for i in range(alerts.MAX_ALERTS):
        assert (
            c.post("/api/me/alerts/", {"filters": {"q": f"modele {i}"}}, format="json").status_code
            == 201
        )
    r = c.post("/api/me/alerts/", {"filters": {"q": "encore"}}, format="json")
    assert r.status_code == 400 and "10" in r.json()["message"]


def test_the_same_search_is_not_saved_twice(buyer):
    c = login(buyer)
    a = c.post("/api/me/alerts/", {"filters": {"q": "iphone"}}, format="json").json()["id"]
    b = c.post("/api/me/alerts/", {"filters": {"q": "iphone"}}, format="json").json()["id"]
    assert a == b and SavedSearch.objects.count() == 1


def test_alerts_belong_to_their_owner(buyer):
    c = login(buyer)
    pk = c.post("/api/me/alerts/", {"filters": {"q": "iphone"}}, format="json").json()["id"]
    other = login(User.objects.create_user(username="o", email="o@t.test", password="x"))
    assert other.get("/api/me/alerts/").json() == []
    assert other.delete(f"/api/me/alerts/{pk}/").status_code == 404
    assert (
        c.patch(f"/api/me/alerts/{pk}/", {"is_active": False}, format="json").json()["is_active"]
        is False
    )
    assert c.delete(f"/api/me/alerts/{pk}/").status_code == 204
    assert APIClient().get("/api/me/alerts/").status_code in (401, 403)


def test_a_new_matching_listing_notifies_once_by_notification_and_email(buyer):
    alert = alerts.create(buyer, {"q": "iphone 13", "price_max": "400000"})
    shop = make_shop()
    listing_after(alert, shop, price=350_000)
    listing_after(alert, shop, price=900_000)  # too expensive
    listing_after(alert, shop, "apple-iphone-12", price=300_000)  # other model
    later = timezone.now() + timedelta(minutes=5)  # the test listings are dated in the future
    assert alerts.run_alerts(now=later) == {"alerts": 1, "notified": 1}
    note = Notification.objects.get()
    assert (
        note.user == buyer
        and "1 nouvelle annonce" in note.title
        and note.url.startswith("/recherche")
    )
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["b@t.test"]
    assert "iPhone 13" in mail.outbox[0].body
    assert alerts.run_alerts()["notified"] == 0  # the cursor moved: nothing is sent twice
    assert Notification.objects.count() == 1 and len(mail.outbox) == 1


def test_listings_published_before_the_alert_do_not_trigger_it(buyer):
    shop = make_shop()
    add_listing(shop, price=300_000)  # already online
    alerts.create(buyer, {"q": "iphone 13"})
    assert alerts.run_alerts()["notified"] == 0


def test_own_listings_inactive_alerts_and_in_app_channel(buyer):
    seller_alert = alerts.create(buyer, {"q": "iphone 13"}, channel="in_app")
    shop = make_shop()
    listing_after(seller_alert, shop)
    mine = add_listing(make_shop(2), published_at=timezone.now() + timedelta(minutes=1))
    mine.seller = buyer
    mine.save()
    paused = alerts.create(buyer, {"q": "ipad"})
    paused.is_active = False
    paused.save()
    listing_after(paused, shop, "apple-ipad-9")
    alerts.run_alerts()
    assert Notification.objects.count() == 1 and mail.outbox == []  # in_app: no e-mail
    assert "2 nouvelles annonces" not in Notification.objects.get().title


def test_many_matches_are_summarised(buyer):
    alert = alerts.create(buyer, {"q": "iphone 13"})
    shop = make_shop()
    for _ in range(5):
        listing_after(alert, shop)
    alerts.run_alerts()
    note = Notification.objects.get()
    assert "5 nouvelles annonces" in note.title and "et 2 autre(s)" in note.body


def test_whatsapp_channel_is_accepted_and_falls_back_on_the_notification(buyer):
    alert = alerts.create(buyer, {"q": "iphone 13"}, channel="whatsapp")
    listing_after(alert, make_shop())
    alerts.run_alerts()
    assert Notification.objects.count() == 1 and mail.outbox == []


def test_notifications_endpoint_and_command(buyer):
    alert = alerts.create(buyer, {"q": "iphone 13"})
    listing_after(alert, make_shop())
    call_command("send_alerts", verbosity=0)
    c = login(buyer)
    body = c.get("/api/me/notifications/").json()
    assert body["unread"] == 1 and body["results"][0]["read"] is False
    assert c.post("/api/me/notifications/").status_code == 204
    assert c.get("/api/me/notifications/").json()["unread"] == 0
    assert (
        login(User.objects.create_user(username="z", email="z@t.test", password="x"))
        .get("/api/me/notifications/")
        .json()["results"]
        == []
    )
