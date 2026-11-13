import json

import httpx
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from trust.tests import GOOD_IMEI, make_listing, make_seller

from . import client as ai_client
from .describe import facts, fallback_text
from .fallback.voice_parser import parse as parse_voice
from .models import AIRequestLog
from .search import _model_tokens


@pytest.fixture
def catalog(db):
    call_command("seed_catalog", verbosity=0)


def phone(seller=None, **extra):
    fields = dict(
        battery_health_pct=86,
        ram_gb=4,
        color="Bleu",
        accessories=["charger", "box"],
        warranty_months=3,
        replaced_parts=["none"],
        network_5g=True,
    )
    fields.update(extra)
    return make_listing(seller or make_seller(1), **fields)


def fake_groq(monkeypatch, *replies):
    queue = list(replies)
    calls = []

    def handler(request):
        calls.append(request)
        reply = queue.pop(0)
        return reply if isinstance(reply, httpx.Response) else httpx.Response(200, json=reply)

    monkeypatch.setattr(
        ai_client,
        "http_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return calls


def chat(payload):
    return {"choices": [{"message": {"content": json.dumps(payload)}}], "usage": {}}


GOOD_TEXT = {
    "title": "Apple iPhone 13 128 Go, bon état",
    "description": " ".join(
        ["Cet iPhone 13 de 128 Go est en bon état, avec une batterie à 86 % de santé."]
        + ["Il est fourni avec son chargeur et sa boîte d'origine, sans pièce remplacée."]
        + ["Le réseau 5G est disponible et la garantie court pendant 3 mois."]
        + ["Les photos montrent l'appareil sous plusieurs angles, vous pouvez le vérifier."] * 3
        + ["Remise en main propre à Cotonou, dans un lieu public, pour tester l'appareil."]
    ),
    "highlights": ["Batterie à 86 %", "Garantie 3 mois", "Chargeur et boîte"],
}


def test_facts_never_contain_personal_data(catalog):
    listing = phone()
    f = facts(listing)
    blob = json.dumps(f, ensure_ascii=False)
    assert GOOD_IMEI not in blob and "example.com" not in blob and "+229" not in blob
    assert f["modele"] == "Apple iPhone 13" and f["sante_batterie_pourcent"] == 86
    assert f["aucune_piece_remplacee"] is True


def test_template_text_states_only_known_facts(catalog):
    listing = phone()
    text = fallback_text(listing, facts(listing))
    assert len(text.title) <= 70 and len(text.highlights) == 3
    assert "Aucune pièce remplacée" in text.description
    assert "86 %" in text.description
    changed = phone(make_seller(2), replaced_parts=["screen"])
    other = fallback_text(changed, facts(changed))
    assert "Aucune pièce remplacée" not in other.description
    assert "Pièces remplacées : screen" in other.description


def test_describe_endpoint_without_a_key(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    listing = phone()
    client.force_login(listing.seller)
    r = client.post(
        "/api/ai/describe/", {"listing_id": listing.pk}, content_type="application/json"
    )
    body = r.json()
    assert r.status_code == 200 and body["used_ai"] is False
    assert body["title"].startswith("Apple iPhone 13")
    assert AIRequestLog.objects.filter(feature="describe", fallback_used=True).exists()


def test_describe_is_limited_to_the_owner(catalog, client):
    listing = phone()
    client.force_login(make_seller(2))
    r = client.post(
        "/api/ai/describe/", {"listing_id": listing.pk}, content_type="application/json"
    )
    assert r.status_code == 404
    client.logout()
    r = client.post(
        "/api/ai/describe/", {"listing_id": listing.pk}, content_type="application/json"
    )
    assert r.status_code in (401, 403)


def test_a_valid_model_text_is_used(catalog, client, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    fake_groq(monkeypatch, chat(GOOD_TEXT))
    listing = phone()
    client.force_login(listing.seller)
    r = client.post(
        "/api/ai/describe/", {"listing_id": listing.pk}, content_type="application/json"
    )
    assert r.json()["used_ai"] is True
    assert r.json()["highlights"] == GOOD_TEXT["highlights"]


@pytest.mark.parametrize(
    "tweak",
    [
        lambda t: {**t, "description": t["description"] + " Batterie neuve à 99 %."},  # invented
        lambda t: {**t, "description": "Trop court."},
        lambda t: {**t, "description": t["description"] + " Jamais réparé."},
    ],
)
def test_invented_or_unsupported_text_is_replaced_by_the_template(
    catalog, client, settings, monkeypatch, tweak
):
    settings.GROQ_API_KEY = "k"
    bad = chat(tweak(GOOD_TEXT))
    fake_groq(monkeypatch, bad, bad)  # the retry is wrong too
    listing = phone(replaced_parts=["screen"])
    client.force_login(listing.seller)
    r = client.post(
        "/api/ai/describe/", {"listing_id": listing.pk}, content_type="application/json"
    )
    assert r.json()["used_ai"] is False


def test_voice_parser_reads_a_dictated_sentence(catalog):
    tokens = _model_tokens()
    out = parse_voice(
        "iPhone 12, 128 giga, batterie 84, petite rayure derrière, avec chargeur",
        known_terms=lambda w: w in tokens,
    )
    assert out.model_text == "iphone 12"
    assert out.category == "smartphone"
    assert out.storage_gb == 128 and out.battery_health_pct == 84
    assert out.accessories == ["charger"]
    assert (out.condition_type, out.grade) == ("used", "B")
    assert "rayure" in out.defects


def audio(size=2000, content_type="audio/webm"):
    return SimpleUploadedFile("dictee.webm", b"a" * size, content_type=content_type)


def test_voice_requires_login_and_rejects_bad_audio(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    assert client.post("/api/ai/voice/", {"audio": audio()}).status_code in (401, 403)
    client.force_login(make_seller(1))
    assert client.post("/api/ai/voice/", {}).status_code == 400
    assert client.post("/api/ai/voice/", {"audio": audio(4 * 1024 * 1024)}).status_code == 400
    assert client.post("/api/ai/voice/", {"audio": audio(), "duration": "75"}).status_code == 400
    assert (
        client.post("/api/ai/voice/", {"audio": audio(content_type="text/plain")}).status_code
        == 400
    )


def test_voice_without_a_key_reports_that_dictation_is_unavailable(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    client.force_login(make_seller(1))
    body = client.post("/api/ai/voice/", {"audio": audio()}).json()
    assert body == {"available": False, "used_ai": False}


def test_voice_fills_the_form_and_finds_the_catalog_model(catalog, client, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    fields = {
        "model_text": "iPhone 12",
        "category": "smartphone",
        "storage_gb": 128,
        "battery_health_pct": 84,
        "condition_type": "used",
        "grade": "B",
        "accessories": ["charger"],
        "defects": "petite rayure derrière",
    }
    calls = fake_groq(monkeypatch, {"text": "iPhone 12, 128 giga, batterie 84"}, chat(fields))
    client.force_login(make_seller(1))
    body = client.post("/api/ai/voice/", {"audio": audio()}).json()
    assert body["available"] and body["used_ai"]
    assert body["fields"]["storage_gb"] == 128 and body["fields"]["grade"] == "B"
    assert body["device_model"]["slug"] == "apple-iphone-12"
    assert b"audio/webm" in calls[0].content  # the recording went to speech to text only
    assert len(calls) == 2 and b"aaaa" not in calls[1].content
    log_features = set(AIRequestLog.objects.values_list("feature", flat=True))
    assert {"voice_stt", "voice_extract"} <= log_features


def test_voice_falls_back_to_rules_when_extraction_fails(catalog, client, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    fake_groq(
        monkeypatch,
        {"text": "Galaxy A54, 128 giga, batterie 90, avec chargeur"},
        httpx.Response(500, json={}),
    )
    client.force_login(make_seller(1))
    body = client.post("/api/ai/voice/", {"audio": audio()}).json()
    assert body["available"] and body["used_ai"] is False
    assert body["fields"]["battery_health_pct"] == 90
    assert body["device_model"]["slug"].startswith("samsung-galaxy-a54")
