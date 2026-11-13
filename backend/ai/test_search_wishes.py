"""Vague wishes (« pc pas cher », « pc gamer », « pc premium ») must still find something."""

import pytest
from django.core.cache import cache as django_cache
from django.core.management import call_command

from insights.factories import add_listing, make_shop
from marketplace.search import search_listings

from .search import fallback_intent, run

pytestmark = pytest.mark.django_db


@pytest.fixture
def stock():
    call_command("seed_catalog", verbosity=0)
    django_cache.clear()
    shop = make_shop()
    laptops = []
    for i, price in enumerate([150, 180, 220, 260, 300, 340, 420, 520, 650, 800]):
        listing = add_listing(shop, "apple-macbook-air-m1", price=price * 1000)
        listing.usage_scores = {"gaming": 2 + i * 0.5, "dev": 4 + i * 0.6, "battery": 6}
        listing.save()
        laptops.append(listing)
    desktop = add_listing(shop, "apple-macbook-air-m1", price=250_000)
    desktop.category = "desktop"
    desktop.save()
    phones = [
        add_listing(shop, "apple-iphone-13", price=p * 1000) for p in (90, 120, 200, 260, 300, 380)
    ]
    return laptops, phones


def results(text):
    payload = run(text)
    listings = list(search_listings(payload["filters"]))
    return payload, listings


@pytest.mark.parametrize(
    "text, tier",
    [
        ("pc pas cher", "cheap"),
        ("ordinateur bon marché", "cheap"),
        ("pc entrée de gamme", "cheap"),
        ("pc abordable", "cheap"),
        ("pc premium", "premium"),
        ("pc haut de gamme", "premium"),
        ("meilleur pc", "premium"),
        ("pc puissant", "premium"),
        ("pc milieu de gamme", "mid"),
        ("pc avec un bon rapport qualité prix", "mid"),
        ("pc à moins de 300000", None),
    ],
)
def test_price_wishes_are_read_as_a_tier(stock, text, tier):
    assert fallback_intent(text).tier == tier


def test_cheap_means_the_lower_third_cheapest_first(stock):
    payload, found = results("pc pas cher")
    prices = [x.price_fcfa for x in found]
    assert prices and prices == sorted(prices)
    assert max(prices) <= 260_000 and len(prices) < 10
    assert any("pas cher" in c["label"] for c in payload["chips"])


def test_premium_means_the_upper_third_dearest_first(stock):
    payload, found = results("pc premium")
    prices = [x.price_fcfa for x in found]
    assert prices and prices == sorted(prices, reverse=True)
    assert min(prices) >= 420_000
    assert any("premium" in c["label"] for c in payload["chips"])


def test_mid_range_sits_between_the_two(stock):
    _, found = results("pc milieu de gamme")
    prices = [x.price_fcfa for x in found]
    assert prices and all(260_000 <= p <= 420_000 for p in prices)


def test_phones_get_their_own_scale(stock):
    _, cheap = results("telephone pas cher")
    _, dear = results("smartphone premium")
    assert max(x.price_fcfa for x in cheap) < min(x.price_fcfa for x in dear)


def test_an_explicit_amount_beats_the_tier(stock):
    payload, found = results("pc pas cher max 200k")
    assert payload["filters"]["price_max"] == "200000"
    assert all(x.price_fcfa <= 200_000 for x in found)


def test_gaming_returns_the_best_available_even_when_none_is_great(stock):
    payload, found = results("pc gamer")
    assert found, "a gaming request must not come back empty"
    scores = [x.usage_scores["gaming"] for x in found]
    assert scores == sorted(scores, reverse=True)
    assert payload["filters"]["sort"] == "usage:gaming"
    assert payload["notes"] and "jeux" in payload["notes"][0]


def test_gaming_keeps_the_strict_bar_when_enough_devices_pass_it(stock):
    laptops, _ = stock
    for x in laptops[-4:]:
        x.usage_scores = {**x.usage_scores, "gaming": 8}
        x.save()
    django_cache.clear()
    payload, found = results("pc gamer")
    assert payload["filters"]["usage"] == "gaming" and "usage_min" not in payload["filters"]
    assert len(found) == 4 and payload["notes"] == []


def test_a_cheap_gaming_pc_combines_both_wishes(stock):
    payload, found = results("pc gamer pas cher")
    assert found and max(x.price_fcfa for x in found) <= 260_000
    assert payload["filters"]["sort"] == "usage:gaming"


def test_nothing_good_enough_falls_back_to_a_ranking(stock):
    laptops, _ = stock
    for x in laptops:
        x.usage_scores = {"gaming": 1}
        x.save()
    payload, found = results("pc gamer")
    assert found and "usage" not in payload["filters"]
    assert "classés" in " ".join(c["label"] for c in payload["chips"])


def test_pc_de_bureau_is_a_desktop_not_an_office_usage(stock):
    i = fallback_intent("pc de bureau")
    assert i.category == "desktop" and i.usage is None
    _, found = results("ordinateur de bureau")
    assert [x.category for x in found] == ["desktop"]


def test_light_and_ultraportable_mean_battery_not_a_model(stock):
    for text in ("pc léger", "pc ultra portable"):
        i = fallback_intent(text)
        assert i.usage == "battery" and i.other_terms == []


def test_words_of_the_wish_do_not_become_model_terms(stock):
    for text in ("pc gamer", "pc premium", "pc gaming pas cher"):
        assert fallback_intent(text).other_terms == []


def test_ordinary_requests_still_work(stock):
    i = fallback_intent("iphone 13 128 go à Cotonou")
    assert i.brands == ["apple"] and i.storage_min == 128 and i.city == "cotonou"
    assert fallback_intent("pc pour coder").usage == "dev"


def test_the_usage_rank_sort_works_from_the_listing_endpoint(stock):
    from rest_framework.test import APIClient

    body = APIClient().get("/api/listings/?category=laptop&sort=usage:gaming").json()
    scores = [r["usage_scores"]["gaming"] for r in body["results"] if r.get("usage_scores")]
    assert scores == sorted(scores, reverse=True) if scores else True
    assert body["count"] == 10
    bad = APIClient().get("/api/listings/?sort=usage:nope")
    assert bad.status_code == 200
