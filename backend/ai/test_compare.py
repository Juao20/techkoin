import json

import httpx
import pytest
from django.core.cache import cache as django_cache
from django.core.management import call_command

from catalog.models import DeviceModel
from marketplace.models import Listing
from pricing import compare as calc
from pricing.services import recompute_listing
from trust.tests import make_listing, make_seller

from . import client as ai_client
from .models import AIRequestLog


@pytest.fixture
def catalog(db):
    call_command("seed_catalog", verbosity=0)
    django_cache.clear()


def phone(n, price, slug="apple-iphone-13", **extra):
    model = DeviceModel.objects.get(slug=slug)
    fields = dict(
        status="active",
        price_fcfa=price,
        device_model=model,
        brand=model.brand,
        imei=f"35{n:013d}",
        ram_gb=4,
        battery_health_pct=90,
    )
    fields.update(extra)
    imei = fields.pop("imei")
    item = make_listing(make_seller(n), imei=imei, **fields)
    recompute_listing(item)
    return item


def trio():
    return [
        phone(1, 300_000, warranty_months=6, accessories=["invoice"]),
        phone(2, 250_000, ram_gb=6),
        phone(3, 280_000, "samsung-galaxy-a54", grade="C"),
    ]


def post(client, ids, **extra):
    return client.post("/api/ai/compare/", {"ids": ids, **extra}, content_type="application/json")


def test_selection_rules(catalog):
    a, b, _ = trio()
    with pytest.raises(calc.CompareError):
        calc.load([a.pk])
    with pytest.raises(calc.CompareError):
        calc.load([a.pk, b.pk, 999999])
    laptop = DeviceModel.objects.filter(category="laptop").first()
    other = make_listing(make_seller(9), imei="35" + "9" * 13, status="active")
    Listing.objects.filter(pk=other.pk).update(category="laptop", device_model=laptop)
    with pytest.raises(calc.CompareError):
        calc.load([a.pk, other.pk])
    draft = phone(8, 100_000, status="draft")
    with pytest.raises(calc.CompareError):
        calc.load([a.pk, draft.pk])


def test_table_marks_the_best_value_of_each_row(catalog):
    a, b, c = trio()
    rows = {r.key: r for r in calc.table([a, b, c])}
    assert rows["price"].best == 1  # cheapest
    assert rows["ram"].best == 1  # 6 Go against 4 Go
    assert rows["warranty"].best == 0
    assert rows["storage"].best is None  # all equal: no best
    assert rows["grade"].values[2].startswith("C")
    assert {"usage_everyday", "usage_photo", "usage_business"} <= set(rows)


def test_deterministic_verdict_weighs_usage_value_and_trust(catalog):
    a, b, c = trio()
    verdict = calc.deterministic_verdict([a, b, c], usage="everyday", budget=None)
    assert verdict["winner_listing_id"] in {a.pk, b.pk, c.pk}
    assert {p["listing_id"] for p in verdict["per_listing"]} == {a.pk, b.pk, c.pk}
    cheap = calc.deterministic_verdict([a, b, c], None, None)["per_listing"]
    assert next(p for p in cheap if p["listing_id"] == b.pk)["best_for"] == "le prix le plus bas"


def test_a_budget_penalises_listings_above_it(catalog):
    a, b, _ = trio()
    free = calc.score(a, None, None)[0]
    capped = calc.score(a, None, 260_000)
    assert capped[0] == pytest.approx(free - 3)
    assert capped[1]["over_budget"] is True
    assert "Au-dessus du budget indiqué" in calc.warnings(a, 260_000)
    assert calc.deterministic_verdict([a, b], None, 260_000)["winner_listing_id"] == b.pk


def test_endpoint_without_a_key_returns_table_verdict_and_cards(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    a, b, c = trio()
    body = post(client, [a.pk, b.pk, c.pk], usage="photo", budget=290_000).json()
    assert body["used_ai"] is False
    assert [x["id"] for x in body["listings"]] == [a.pk, b.pk, c.pk]
    assert body["verdict"]["winner_listing_id"] in {a.pk, b.pk, c.pk}
    assert any(r["key"] == "price" for r in body["rows"])
    assert "thumb" in body["listings"][0] and "imei" not in json.dumps(body).lower()


def test_endpoint_validation(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    a, b, _ = trio()
    assert post(client, [a.pk]).status_code == 400
    assert post(client, [a.pk, b.pk], usage="office").status_code == 400  # PC usage on phones
    assert post(client, "abc").status_code == 400


def test_results_are_cached_until_a_listing_changes(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    a, b, _ = trio()
    first = post(client, [a.pk, b.pk]).json()
    again = post(client, [b.pk, a.pk]).json()  # order does not matter for the cache key
    assert again["verdict"] == first["verdict"]
    assert AIRequestLog.objects.filter(feature="compare", cache_hit=True).count() == 1
    a.price_fcfa = 100_000
    a.save()
    changed = post(client, [a.pk, b.pk]).json()
    assert changed["verdict"]["winner_listing_id"] == a.pk


def groq(monkeypatch, payload, seen=None):
    def handler(request):
        if isinstance(payload, Exception):
            raise payload
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(payload)}}], "usage": {}}
        )

    def make(timeout):
        if seen is not None:
            seen.append(timeout)
        return httpx.Client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(ai_client, "http_client", make)


def model_verdict(a, b, winner=None, summary="Le premier est plus économique."):
    return {
        "winner_listing_id": winner or b.pk,
        "summary": summary,
        "reasons": ["Prix plus bas"],
        "warnings": [],
        "per_listing": [
            {"listing_id": a.pk, "best_for": "garantie", "verdict_line": "Plus cher"},
            {"listing_id": b.pk, "best_for": "prix", "verdict_line": "Moins cher"},
        ],
    }


def test_a_valid_model_verdict_is_used_with_a_short_timeout(catalog, client, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    a, b, _ = trio()
    seen = []
    groq(monkeypatch, model_verdict(a, b), seen)
    body = post(client, [a.pk, b.pk]).json()
    assert body["used_ai"] is True and body["verdict"]["winner_listing_id"] == b.pk
    assert seen == [settings.AI_COMPARE_TIMEOUT_SECONDS]  # the 3 second promise


def test_a_winner_outside_the_comparison_is_rejected(catalog, client, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    a, b, c = trio()
    groq(monkeypatch, model_verdict(a, b, winner=c.pk))
    body = post(client, [a.pk, b.pk]).json()
    assert body["used_ai"] is False
    assert body["verdict"]["winner_listing_id"] in {a.pk, b.pk}


def test_invented_numbers_are_rejected(catalog, client, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    a, b, _ = trio()
    groq(monkeypatch, model_verdict(a, b, summary="Il est 42 % moins cher et dure 31 heures."))
    assert post(client, [a.pk, b.pk]).json()["used_ai"] is False


def test_a_timeout_falls_back_to_the_deterministic_verdict(catalog, client, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    a, b, _ = trio()
    groq(monkeypatch, httpx.ReadTimeout("trop lent"))
    body = post(client, [a.pk, b.pk]).json()
    assert body["used_ai"] is False and body["verdict"]["winner_listing_id"]


def test_alternatives_are_picked_by_django(catalog, client):
    a = phone(1, 300_000)
    near = phone(2, 310_000, "samsung-galaxy-a54")
    near2 = phone(3, 270_000, "apple-iphone-12")
    phone(4, 900_000, "apple-iphone-12")  # too expensive
    phone(5, 300_000)  # same model as the listing: not an alternative
    r = client.get(f"/api/ai/compare/suggestions/?listing_id={a.pk}").json()
    assert {x["id"] for x in r} == {near.pk, near2.pk}


def test_compare_limits_for_visitors(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    settings.AI_LIMITS = {**settings.AI_LIMITS, "compare": (2, 4)}
    a, b, _ = trio()
    codes = [post(client, [a.pk, b.pk], budget=100_000 + n).status_code for n in range(3)]
    assert codes == [200, 200, 429]
