import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from insights.factories import add_listing, make_shop

from .search import search_listings

pytestmark = pytest.mark.django_db


@pytest.fixture
def stock():
    call_command("seed_catalog", verbosity=0)
    a, b = make_shop(1), make_shop(2, city="Parakou")
    add_listing(a, "apple-iphone-13", price=300_000, grade="A", warranty_months=6)
    add_listing(a, "apple-iphone-13", price=320_000, grade="B")
    add_listing(b, "apple-iphone-12", price=250_000, grade="B", warranty_months=3)
    add_listing(b, "apple-macbook-air-m1", price=500_000, grade="A")
    add_listing(b, "apple-iphone-13", price=280_000, status="sold")  # never counted


def get(query=""):
    return APIClient().get(f"/api/listings/facets/{query}").json()


def test_counts_follow_the_whole_search(stock):
    body = get()
    assert body["total"] == 4
    assert body["category"] == {"smartphone": 3, "laptop": 1}
    assert body["brand"] == {"apple": 4}
    assert body["grade"] == {"A": 2, "B": 2}
    assert body["seller_type"] == {"shop": 4, "individual": 0}
    assert body["flags"]["warranty"] == 2


def test_a_group_ignores_its_own_filter_but_not_the_others(stock):
    body = get("?category=laptop&grade=A")
    assert body["total"] == 1
    # category counts keep the grade filter but not the category one
    assert body["category"] == {"smartphone": 1, "laptop": 1}
    # grade counts keep the category filter but not the grade one
    assert body["grade"] == {"A": 1}


def test_flags_count_what_checking_them_would_leave(stock):
    assert get("?category=smartphone")["flags"]["warranty"] == 2
    assert get("?q=iphone+13")["flags"]["warranty"] == 1


def test_counts_match_the_real_search(stock):
    for query in ("?category=smartphone", "?q=iphone", "?price_max=300000"):
        params = dict(p.split("=") for p in query[1:].split("&"))
        assert get(query)["total"] == search_listings(params).count()


def test_warranty_accepts_a_number_of_months(stock):
    assert search_listings({"warranty": "6"}).count() == 1
    assert search_listings({"warranty": "3"}).count() == 2
    assert search_listings({"warranty": "1"}).count() == 2
