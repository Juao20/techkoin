import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from analytics.models import Event
from insights.factories import add_events, add_listing, make_shop

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def catalog():
    call_command("seed_catalog", verbosity=0)


def get(shop, query=""):
    c = APIClient()
    c.force_login(shop.owner)
    return c.get(f"/api/shop/stats/{query}")


def test_counts_only_the_shops_own_events():
    mine, other = make_shop(1), make_shop(2)
    a, b = add_listing(mine), add_listing(other)
    add_events("listing_view", 10, listing=a, shop=mine)
    add_events("whatsapp_click", 2, listing=a, shop=mine)
    add_events("phone_reveal", 1, listing=a, shop=mine)
    add_events("favorite_add", 4, listing=a, shop=mine)
    add_events("listing_view", 99, listing=b, shop=other)
    body = get(mine, "?period=7").json()
    assert body["totals"]["views"] == 10
    assert body["totals"]["contacts"] == 3
    assert body["totals"]["favorites"] == 4
    assert body["totals"]["contact_rate"] == 30.0
    assert [row["id"] for row in body["listings"]] == [a.pk]


def test_compares_with_the_previous_period():
    shop = make_shop()
    listing = add_listing(shop)
    add_events("listing_view", 15, days_ago=2, listing=listing, shop=shop)
    add_events("listing_view", 10, days_ago=10, listing=listing, shop=shop)
    body = get(shop, "?period=7").json()
    assert body["totals"]["views"] == 15
    assert body["previous"]["views"] == 10
    assert body["totals"]["change"]["views"] == 50


def test_series_has_one_point_per_day():
    shop = make_shop()
    assert len(get(shop, "?period=7").json()["series"]) == 7
    assert len(get(shop, "?period=90").json()["series"]) == 90
    assert get(shop, "?period=12").json()["period"] == 30  # unknown periods fall back


def test_free_shops_get_their_dashboard_too():
    assert get(make_shop(plan="free")).status_code == 200


def test_individuals_are_refused():
    from accounts.models import User

    user = User.objects.create_user(username="p", email="p@t.test", password="x")
    c = APIClient()
    c.force_login(user)
    assert c.get("/api/shop/stats/").status_code == 403
    assert APIClient().get("/api/shop/stats/").status_code in (401, 403)


def test_sold_listings_make_the_revenue():
    from datetime import timedelta

    from django.utils import timezone

    shop = make_shop()
    add_listing(shop, price=250_000, status="sold", sold_at=timezone.now() - timedelta(days=2))
    body = get(shop, "?period=7").json()
    assert (body["totals"]["sales"], body["totals"]["revenue_fcfa"]) == (1, 250_000)
    assert Event.objects.count() == 0
