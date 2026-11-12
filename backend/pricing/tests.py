from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from accounts.models import User
from catalog.models import DeviceModel
from marketplace.models import Listing

from .estimate import Estimate, estimate, price_badge, round_price
from .usage import advised_usage, scale, usage_scores


@pytest.fixture
def catalog(db):
    call_command("seed_catalog", verbosity=0)


@pytest.fixture
def seller(db):
    return User.objects.create_user(username="s", email="s@example.com", password="x-y-z-12345")


def add(seller, model, price, grade="B", status="active", storage=128, **extra):
    return Listing.objects.create(
        seller=seller,
        device_model=model,
        category=model.category,
        brand=model.brand,
        condition_type=extra.pop("condition_type", "used"),
        grade=grade,
        price_fcfa=price,
        storage_gb=storage,
        status=status,
        sold_at=timezone.now() - timedelta(days=10) if status == "sold" else None,
        slug=f"l-{Listing.objects.count()}",
        **extra,
    )


def iphone(**kw):
    return DeviceModel.objects.get(slug="apple-iphone-13")


def test_rounding_to_5000():
    assert round_price(302_400) == 300_000
    assert round_price(303_000) == 305_000


def test_estimate_uses_median_of_comparables_normalised_to_grade_b(catalog, seller):
    model = iphone()
    for price in (290_000, 300_000, 300_000, 310_000, 300_000):
        add(seller, model, price)
    b = estimate(model, storage_gb=128, condition_type="used", grade="B")
    assert not b.indicative and b.sample_size == 5
    assert b.mid == 300_000 and b.low <= b.mid <= b.high
    a = estimate(model, storage_gb=128, condition_type="used", grade="A")
    assert a.mid == round_price(300_000 * 1.08)
    c = estimate(model, storage_gb=128, condition_type="used", grade="C")
    assert c.mid == round_price(300_000 * 0.85)


def test_low_battery_and_replaced_parts_lower_the_estimate(catalog, seller):
    model = iphone()
    for price in (300_000,) * 5:
        add(seller, model, price)
    base = estimate(model, storage_gb=128, grade="B")
    worn = estimate(
        model, storage_gb=128, grade="B", battery_health_pct=75, replaced_parts=["screen"]
    )
    assert worn.mid == round_price(300_000 * 0.95 * 0.92)
    assert worn.mid < base.mid


def test_outliers_are_excluded(catalog, seller):
    model = iphone()
    for price in (298_000, 300_000, 300_000, 302_000, 301_000, 299_000, 1_500_000):
        add(seller, model, price)
    est = estimate(model, storage_gb=128, grade="B")
    assert est.mid == 300_000
    assert est.sample_size == 6


def test_recent_sales_count_more_and_old_sales_are_ignored(catalog, seller):
    model = iphone()
    for price in (250_000,) * 3:
        add(seller, model, price)
    for price in (350_000,) * 3:
        add(seller, model, price, status="sold")
    old = add(seller, model, 100_000, status="sold")
    Listing.objects.filter(pk=old.pk).update(sold_at=timezone.now() - timedelta(days=200))
    est = estimate(model, storage_gb=128, grade="B")
    assert est.sample_size == 6
    assert est.mid > 300_000  # unweighted median would be 300 000; sold listings weigh 1.5


def test_few_comparables_give_an_indicative_estimate(catalog, seller):
    model = iphone()
    add(seller, model, 300_000)
    est = estimate(model, storage_gb=128, grade="B")
    assert est.indicative and est.sample_size == 0
    assert est.low < est.mid < est.high
    assert est.mid <= model.reference_price_new_fcfa


def test_no_estimate_without_a_catalog_model():
    assert estimate(None) is None


def test_badges_follow_the_thresholds():
    est = Estimate(low=270_000, mid=300_000, high=330_000, sample_size=8, indicative=False)
    assert price_badge(270_000, est) == "good_deal"  # 0.90
    assert price_badge(300_000, est) == "fair"
    assert price_badge(330_000, est) == "fair"  # 1.10
    assert price_badge(335_000, est) == "unknown"  # between 1.10 and 1.15
    assert price_badge(345_000, est) == "above_market"  # 1.15
    indicative = Estimate(low=1, mid=300_000, high=3, sample_size=0, indicative=True)
    assert price_badge(100_000, indicative) == "unknown"
    assert price_badge(100_000, None) == "unknown"


def test_scale_interpolates_and_clamps():
    points = [(4, 3), (8, 6)]
    assert scale(2, points) == 3
    assert scale(6, points) == 4.5
    assert scale(64, points) == 6
    assert scale(None, points) == 5


def test_usage_scores_are_bounded_and_ranked(catalog, seller):
    gaming = DeviceModel.objects.filter(category="laptop", default_gpu__dedicated=True).first()
    office = DeviceModel.objects.filter(category="laptop", default_gpu__isnull=True).first()
    g = add(
        seller,
        gaming,
        800_000,
        ram_gb=16,
        storage_type="ssd",
        storage=512,
        processor=gaming.default_processor,
        gpu=gaming.default_gpu,
        refresh_rate_hz=144,
    )
    o = add(
        seller,
        office,
        300_000,
        ram_gb=8,
        storage_type="ssd",
        storage=256,
        processor=office.default_processor,
        refresh_rate_hz=60,
    )
    gs, os_ = usage_scores(g), usage_scores(o)
    assert set(gs) == {"office", "study", "dev", "gaming", "creative", "battery"}
    assert all(0 <= v <= 10 for v in (*gs.values(), *os_.values()))
    assert gs["gaming"] > os_["gaming"]


def test_dev_score_follows_the_documented_formula(catalog, seller):
    model = DeviceModel.objects.filter(category="laptop", default_processor__isnull=False).first()
    listing = add(
        seller,
        model,
        500_000,
        ram_gb=16,
        storage_type="ssd",
        storage=512,
        processor=model.default_processor,
        screen_resolution="1920x1080",
        refresh_rate_hz=60,
    )
    cpu = model.default_processor.perf_score / 10
    ram = 8.0  # 16 Go
    ssd = 0.6 * 10 + 0.4 * 8  # SSD, 512 Go
    screen = (6 + 4) / 2  # full HD, 60 Hz
    expected = 0.45 * cpu + 0.30 * ram + 0.15 * ssd + 0.10 * screen
    assert usage_scores(listing)["dev"] == pytest.approx(expected, abs=0.1)


def test_mobile_usages_and_advised_usage(catalog, seller):
    phone = DeviceModel.objects.filter(category="smartphone").first()
    listing = add(seller, phone, 200_000, ram_gb=8, battery_health_pct=95)
    scores = usage_scores(listing)
    assert set(scores) == {"everyday", "photo", "gaming", "battery", "business"}
    assert advised_usage({"office": 6.9, "dev": 6.0}) is None
    assert advised_usage({"office": 7.0, "dev": 6.0}) == "office"
    assert advised_usage({}) is None


def test_estimate_endpoint_returns_range_and_badge(catalog, seller, client):
    model = iphone()
    for price in (300_000,) * 5:
        add(seller, model, price)
    r = client.post(
        "/api/pricing/estimate/",
        {"device_model": model.slug, "storage_gb": 128, "grade": "B", "price_fcfa": 250_000},
        content_type="application/json",
    )
    assert r.status_code == 200
    body = r.json()
    assert body["available"] and body["mid"] == 300_000 and body["badge"] == "good_deal"
    assert not body["indicative"]


def test_recompute_estimates_command_updates_listings(catalog, seller):
    model = iphone()
    listings = [add(seller, model, 300_000, ram_gb=6) for _ in range(6)]
    call_command("recompute_estimates", verbosity=0)
    first = Listing.objects.get(pk=listings[0].pk)
    assert first.estimate_mid == 300_000
    assert first.price_badge == "fair"
    assert first.usage_scores
