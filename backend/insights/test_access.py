"""Spec 19, phase 5: a Free shop cannot call the Pro endpoints (403) and only previews P1 to P3."""

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from accounts.models import User

from .factories import add_events, add_listing, make_shop

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def catalog():
    call_command("seed_catalog", verbosity=0)


def login(user) -> APIClient:
    c = APIClient()
    c.force_login(user)
    return c


PRO_ONLY = [
    ("get", "/api/insights/reports/", None),
    ("post", "/api/insights/reports/", {}),
    ("get", "/api/insights/reports/1/", None),
    ("post", "/api/insights/chat/", {"question": "Combien de vues ?"}),
    ("post", "/api/insights/bulk-optimize/", {"listing_ids": [1]}),
    ("post", "/api/insights/bulk-optimize/apply/", {"items": []}),
    ("get", "/api/insights/competition/1/", None),
    ("post", "/api/insights/listings/1/apply/", {"price_fcfa": 100000}),
]
PREVIEW = ["/api/insights/demand/", "/api/insights/pricing/", "/api/insights/dormant/"]


@pytest.mark.parametrize("method,url,body", PRO_ONLY)
def test_free_shop_gets_403_on_every_pro_endpoint(method, url, body):
    free = make_shop(1, plan="free")
    add_listing(free)
    r = getattr(login(free.owner), method)(url, body, format="json")
    assert r.status_code == 403, url
    assert r.json()["code"] == "forbidden"
    assert "Pro" in r.json()["message"]


@pytest.mark.parametrize("method,url,body", PRO_ONLY)
def test_an_expired_pro_plan_is_refused_too(method, url, body):
    from datetime import timedelta

    from django.utils import timezone

    shop = make_shop(1, plan="pro")
    shop.plan_expires_at = timezone.now() - timedelta(hours=1)
    shop.save()
    assert getattr(login(shop.owner), method)(url, body, format="json").status_code == 403


@pytest.mark.parametrize("method,url,body", PRO_ONLY + [("get", u, None) for u in PREVIEW])
def test_individuals_and_visitors_are_refused(method, url, body):
    person = User.objects.create_user(username="p", email="p@t.test", password="x")
    assert getattr(login(person), method)(url, body, format="json").status_code == 403
    assert getattr(APIClient(), method)(url, body, format="json").status_code in (401, 403)


def test_a_free_shop_never_receives_pro_content_in_its_previews():
    free = make_shop(1, plan="free")
    for days in range(40, 44):
        add_listing(free, price=900_000, days_online=days, estimate_mid=300_000)
    add_events("search", 12, query_text="iphone 13", filters={"q": "iphone 13"}, city="cotonou")
    add_events("search", 12, query_text="tecno spark", filters={"q": "tecno spark"})
    c = login(free.owner)

    demand = c.get("/api/insights/demand/").json()
    assert demand["preview"] is True and len(demand["rows"]) == 1 and demand["hidden"] >= 1
    assert "recommendations" not in demand

    pricing = c.get("/api/insights/pricing/").json()
    assert pricing["preview"] is True and len(pricing["rows"]) == 1 and pricing["hidden"] == 3
    assert pricing["used_ai"] is False

    dormant = c.get("/api/insights/dormant/").json()
    assert dormant["preview"] is True and len(dormant["rows"]) <= 1
    assert all(row["fix"] is None for row in dormant["rows"])


def test_a_pro_shop_gets_everything():
    pro = make_shop(1)
    for _ in range(3):
        add_listing(pro, price=900_000, estimate_mid=300_000)
    pricing = login(pro.owner).get("/api/insights/pricing/").json()
    assert pricing["preview"] is False and len(pricing["rows"]) == 3 and pricing["hidden"] == 0


def test_the_shop_dashboard_stats_stay_open_to_free_shops():
    assert login(make_shop(1, plan="free").owner).get("/api/shop/stats/").status_code == 200
