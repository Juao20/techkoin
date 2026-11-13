"""P1 radar, P2 price advice, P3 dormant stock: computed from events and listings, not invented."""

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from analytics.models import Event

from . import demand, dormant, pricing_advice
from .factories import add_events, add_listing, make_shop

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def catalog():
    call_command("seed_catalog", verbosity=0)


def search(query, n, days_ago=1, city="cotonou", no_result=False, **filters):
    return add_events(
        "search_no_result" if no_result else "search",
        n,
        days_ago=days_ago,
        query_text=query,
        filters={"q": query, "city": city, **filters},
        city=city,
    )


# ------------------------------------------------------------------ P1


def test_radar_counts_exactly_the_simulated_searches():
    shop = make_shop()
    search("macbook m1", 9, price_max="400000")
    search("macbook m1", 5, no_result=True, price_max="350000")
    search("iphone 13", 11)
    rows = demand.radar(shop, 7)["rows"]
    mac = next(r for r in rows if r["label"] == "macbook m1" and r["city"] == "Cotonou")
    assert mac["searches"] == 14 and mac["no_result"] == 5
    assert mac["budget_max"] == 400_000 and mac["budget_label"] == "moins de 400 000 FCFA"
    assert mac["category"] == "laptop"
    assert mac["median_budget_fcfa"] == 400_000


def test_radar_hides_segments_under_ten_searches():
    shop = make_shop()
    search("macbook m1", 9)
    search("ipad", 10)
    labels = {r["label"] for r in demand.radar(shop, 7)["rows"]}
    assert "ipad" in labels and "macbook m1" not in labels


def test_a_thin_city_still_counts_in_the_all_cities_row():
    shop = make_shop()
    for city in ("cotonou", "parakou", "bohicon"):
        search("tecno spark", 4, city=city)
    rows = [r for r in demand.radar(shop, 7)["rows"] if r["label"] == "tecno spark"]
    assert len(rows) == 1 and rows[0]["city"] is None and rows[0]["searches"] == 12


def test_radar_compares_demand_with_supply_and_the_previous_period():
    shop = make_shop()
    add_listing(shop, "apple-iphone-13")  # one iPhone 13 on sale, in Cotonou
    add_listing(make_shop(2), "apple-iphone-13", city="Parakou")
    search("iphone 13", 20)
    search("iphone 13", 5, city="parakou")
    search("iphone 13", 10, days_ago=9)
    rows = [r for r in demand.radar(shop, 7)["rows"] if r["label"] == "iphone 13"]
    national = next(r for r in rows if r["city"] is None)
    assert national["searches"] == 25 and national["supply"] == 2 and national["my_supply"] == 1
    assert national["previous_searches"] == 10 and national["change_pct"] == 150
    assert national["searches_per_listing"] == 12.5
    cotonou = next(r for r in rows if r["city"] == "Cotonou")  # city rows only see local stock
    assert cotonou["searches"] == 20 and cotonou["supply"] == 1


def test_strong_demand_with_weak_supply_comes_first():
    shop = make_shop()
    for _ in range(5):
        add_listing(shop, "apple-iphone-13")
    search("iphone 13", 40)
    search("macbook m1", 15)
    labels = [r["label"] for r in demand.radar(shop, 7)["rows"]]
    assert labels.index("macbook m1") < labels.index("iphone 13")


def test_searches_made_with_filters_only_are_described_by_category():
    shop = make_shop()
    add_events(
        "search", 12, filters={"category": "laptop", "brand": "hp"}, query_text="", city="cotonou"
    )
    row = demand.radar(shop, 7)["rows"][0]
    assert row["label"] == "PC portables Hp" and row["category"] == "laptop"


def test_the_radar_endpoint_returns_recommendations_for_pro_shops():
    pro = make_shop()
    search("macbook m1", 30)
    c = APIClient()
    c.force_login(pro.owner)
    body = c.get("/api/insights/demand/?period=7").json()
    assert body["rows"][0]["searches"] == 30
    assert body["recommendations"] and "macbook m1" in body["recommendations"][0]
    assert body["used_ai"] is False  # no Groq key in tests: deterministic wording


# ------------------------------------------------------------------ P2


def test_a_price_far_above_the_estimate_is_advised_down_by_rounded_steps():
    shop = make_shop()
    listing = add_listing(
        shop, price=420_000, estimate_mid=300_000, estimate_low=280_000, estimate_high=320_000
    )
    listing.estimate_sample_size = 8
    listing.save()
    advice = pricing_advice.advise(listing)
    assert advice["action"] == "lower" and advice["gap_pct"] == 40
    assert advice["advised_price_fcfa"] == 315_000 and advice["advised_price_fcfa"] % 5000 == 0


def test_a_price_below_the_estimate_can_be_raised_and_a_fair_one_is_kept():
    shop = make_shop()
    cheap = add_listing(shop, price=200_000, estimate_mid=300_000, estimate_sample_size=8)
    fair = add_listing(shop, price=310_000, estimate_mid=300_000, estimate_sample_size=8)
    assert pricing_advice.advise(cheap)["action"] == "raise"
    assert pricing_advice.advise(cheap)["advised_price_fcfa"] == 290_000
    assert pricing_advice.advise(fair)["action"] == "keep"


def test_an_indicative_estimate_needs_a_wider_gap_before_advising():
    shop = make_shop()
    listing = add_listing(shop, price=345_000, estimate_mid=300_000, estimate_sample_size=2)
    advice = pricing_advice.advise(listing)
    assert advice["action"] == "keep" and advice["indicative"] is True


def test_no_estimate_means_no_advice():
    listing = add_listing(make_shop(), price=300_000)
    assert pricing_advice.advise(listing)["action"] == "none"


def test_pricing_rows_compare_activity_with_the_category_average():
    shop = make_shop()
    mine = add_listing(shop)
    other = add_listing(make_shop(2))
    add_events("listing_view", 10, listing=mine, shop=shop)
    add_events("whatsapp_click", 4, listing=mine, shop=shop)
    add_events("listing_view", 2, listing=other, shop=other.shop)
    row = pricing_advice.rows(shop)[0]
    assert (row["views"], row["contacts"]) == (10, 4)
    assert row["category_avg_views"] == 6.0 and row["category_avg_contacts"] == 2.0


def test_apply_the_advised_price(client=None):
    pro = make_shop()
    listing = add_listing(pro, price=420_000, estimate_mid=300_000, estimate_sample_size=8)
    c = APIClient()
    c.force_login(pro.owner)
    r = c.post(
        f"/api/insights/listings/{listing.pk}/apply/", {"price_fcfa": 315_000}, format="json"
    )
    assert r.status_code == 200 and r.json()["changed"] == ["price"]
    listing.refresh_from_db()
    assert listing.price_fcfa == 315_000 and listing.last_price_change_at is not None
    bad = c.post(f"/api/insights/listings/{listing.pk}/apply/", {"price_fcfa": -5}, format="json")
    assert bad.status_code == 400
    other = add_listing(make_shop(2))
    assert (
        c.post(
            f"/api/insights/listings/{other.pk}/apply/", {"price_fcfa": 1000}, format="json"
        ).status_code
        == 404
    )


# ------------------------------------------------------------------ P3


def old(shop, **kw):
    return add_listing(shop, days_online=30, **kw)


def test_dormant_listings_are_old_and_convert_below_the_median():
    shop = make_shop()
    sleeper = old(shop, description="")
    busy, busier = old(shop, description=""), old(shop, description="")
    fresh = add_listing(shop, days_online=3)
    add_events("listing_view", 40, listing=sleeper, shop=shop)
    add_events("whatsapp_click", 1, listing=sleeper, shop=shop)
    for popular in (busy, busier):
        add_events("listing_view", 40, listing=popular, shop=shop)
        add_events("whatsapp_click", 12, listing=popular, shop=shop)
    add_events("listing_view", 40, listing=fresh, shop=shop)
    ids = [r["id"] for r in dormant.diagnose(shop, with_fixes=False)["rows"]]
    assert ids == [sleeper.pk]


def test_causes_come_from_rules():
    shop = make_shop()
    sleeper = old(shop, price=500_000, estimate_mid=300_000, estimate_sample_size=9, description="")
    add_events("listing_view", 30, listing=sleeper, shop=shop)
    other = old(shop)
    add_events("listing_view", 30, listing=other, shop=shop)
    add_events("whatsapp_click", 10, listing=other, shop=shop)
    row = next(r for r in dormant.diagnose(shop, with_fixes=False)["rows"] if r["id"] == sleeper.pk)
    codes = {c["code"] for c in row["causes"]}
    assert {"price_above_market", "few_photos", "short_description"} <= codes
    assert row["advised_price_fcfa"] == 315_000
    assert row["note"]


def test_a_listing_with_photos_and_a_full_description_is_not_blamed_for_them():
    from marketplace.models import ListingPhoto

    shop = make_shop()
    good = old(shop, description=" ".join(["mot"] * 60))
    for i in range(6):
        ListingPhoto.objects.create(listing=good, image=f"x{i}.webp", thumb=f"t{i}.webp")
    add_events("listing_view", 30, listing=good, shop=shop)
    peer = old(shop)
    add_events("listing_view", 30, listing=peer, shop=shop)
    add_events("whatsapp_click", 10, listing=peer, shop=shop)
    row = next(r for r in dormant.diagnose(shop, with_fixes=False)["rows"] if r["id"] == good.pk)
    codes = {c["code"] for c in row["causes"]}
    assert "few_photos" not in codes and "short_description" not in codes


def test_dormant_fix_is_a_checked_f2_text():
    shop = make_shop()
    sleeper = old(shop, description="")
    add_events("listing_view", 30, listing=sleeper, shop=shop)
    peer = old(shop)
    add_events("listing_view", 30, listing=peer, shop=shop)
    add_events("whatsapp_click", 10, listing=peer, shop=shop)
    row = next(r for r in dormant.diagnose(shop)["rows"] if r["id"] == sleeper.pk)
    assert row["fix"]["title"] and len(row["fix"]["description"].split()) >= 10
    assert Event.objects.filter(listing=sleeper).count() == 30
