import json

import httpx
import pytest
from django.core.cache import cache as django_cache
from django.core.management import call_command

from . import client as ai_client
from .fallback.query_parser import parse_amounts, plain
from .models import AIRequestLog
from .search import fallback_intent, run


@pytest.fixture
def catalog(db):
    call_command("seed_catalog", verbosity=0)
    django_cache.clear()


def intent(text):
    return fallback_intent(text)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("max 250k", (None, 250_000)),
        ("pas plus de 250 000", (None, 250_000)),
        ("budget 250mil", (None, 250_000)),
        ("vers 1,5 million", (None, 1_500_000)),
        ("250.000 fcfa", (None, 250_000)),
        ("entre 100 et 200k", (100_000, 200_000)),
        ("à partir de 300k", (300_000, None)),
        ("iphone 13 de 128 go", (None, None)),
        ("16 go de ram et 512 go", (None, None)),
        ("un pc", (None, None)),
    ],
)
def test_amounts(text, expected):
    low, high, _ = parse_amounts(plain(text))
    assert (low, high) == expected


def test_the_example_of_the_spec(catalog):
    i = intent("un pc pour coder pas trop cher vers Calavi, max 250k")
    assert i.category == "laptop"
    assert i.usage == "dev"
    assert i.city == "abomey-calavi"
    assert i.price_max == 250_000 and i.price_min is None
    assert i.confidence >= 0.5


def test_brand_model_and_storage(catalog):
    i = intent("iPhone 13 128 Go d'occasion à Cotonou")
    assert i.brands == ["apple"]
    assert i.category == "smartphone"
    assert i.storage_min == 128
    assert i.condition == ["used"]
    assert i.city == "cotonou"
    assert i.other_terms[:2] == ["iphone", "13"]


def test_ram_storage_and_keyboard(catalog):
    i = intent("pc portable 16 go de ram 512 go ssd azerty")
    assert (i.category, i.ram_min, i.storage_min, i.keyboard) == ("laptop", 16, 512, "azerty")


def test_condition_words(catalog):
    assert intent("samsung neuf").condition == ["new_sealed", "new_open"]
    assert intent("pc comme neuf").grade == ["A"]
    assert intent("tablette reconditionnée").condition == ["refurbished"]
    assert intent("tablette").category == "tablet"


def test_usage_words_follow_the_category(catalog):
    assert intent("pc pour jouer à fortnite").usage == "gaming"
    assert intent("ordinateur pour l'école").usage == "study"
    assert intent("laptop montage vidéo").usage == "creative"
    assert intent("téléphone pour la photo").usage == "photo"


def test_nothing_recognised_gives_low_confidence(catalog):
    i = intent("bonjour")
    assert i.confidence <= 0.2 and not i.model_dump(exclude={"confidence"}, exclude_defaults=True)


def test_endpoint_without_a_key_uses_the_rules_and_is_cached(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    body = {"query": "un pc pour coder vers Calavi max 250k"}
    first = client.post("/api/ai/search/", body, content_type="application/json").json()
    assert first["used_ai"] is False
    assert first["filters"] == {
        "category": "laptop",
        "price_max": "250000",
        "city": "abomey-calavi",
        "usage": "dev",
    }
    assert [c["label"] for c in first["chips"]][:2] == ["PC portable", "max 250 000 FCFA"]
    assert first["chips"][1]["keys"] == ["price_max"]
    second = client.post("/api/ai/search/", body, content_type="application/json").json()
    assert second == first
    assert AIRequestLog.objects.filter(feature="search", cache_hit=True).count() == 1


def test_endpoint_rejects_an_empty_query(catalog, client):
    assert (
        client.post("/api/ai/search/", {"query": " "}, content_type="application/json").status_code
        == 400
    )


def test_model_answer_is_sanitised_against_the_catalog(catalog, client, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    answer = {
        "category": "laptop",
        "brands": ["dell", "marque-inconnue"],
        "price_min": 300000,
        "price_max": 100000,
        "city": "atlantide",
        "condition": ["used"],
        "usage": "dev",
        "other_terms": ["Latitude"],
        "confidence": 0.8,
    }

    def handler(request):
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(answer)}}], "usage": {}}
        )

    monkeypatch.setattr(
        ai_client,
        "http_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = run("un dell pas cher")
    assert result["used_ai"] is True
    f = result["filters"]
    assert f["brand"] == "dell"  # unknown brand dropped
    assert "city" not in f  # unknown city dropped
    assert (f["price_min"], f["price_max"]) == ("100000", "300000")  # swapped back
    assert f["q"] == "latitude"


def test_search_limits_by_visitor_and_by_user(catalog, client, settings, django_user_model):
    settings.GROQ_API_KEY = ""
    settings.AI_LIMITS = {**settings.AI_LIMITS, "search": (2, 4)}
    post = lambda q: client.post(  # noqa: E731
        "/api/ai/search/", {"query": q}, content_type="application/json"
    ).status_code
    assert [post(f"pc {n}") for n in range(3)] == [200, 200, 429]
    django_cache.clear()
    user = django_user_model.objects.create_user("u", "u@example.com", "x-y-z-12345")
    client.force_login(user)
    assert [post(f"pc {n}") for n in range(5)] == [200, 200, 200, 200, 429]
