"""Acceptance test for phase 3: no personal data goes to the language model, whatever feature."""

import json

import httpx
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from marketplace import services
from trust.tests import GOOD_IMEI, make_listing, make_seller

from . import client as ai_client
from . import prompts
from .models import AIRequestLog

SECRETS = [
    "Koffi",
    "Adjovi",
    "+22901971234",
    "01 97 12 34 56",
    "0197123456",
    "55 44 33",
    "seller.private@example.com",
    "moi@example.net",
    GOOD_IMEI,
]


@pytest.fixture
def world(db, settings, monkeypatch):
    call_command("seed_catalog", verbosity=0)
    settings.GROQ_API_KEY = "k"
    seller = make_seller(1)
    seller.first_name, seller.last_name = "Koffi", "Adjovi"
    seller.email = "seller.private@example.com"
    seller.phone = "+2290197123456"
    seller.whatsapp_number = "+2290197123456"
    seller.save()
    listing = make_listing(
        seller,
        status="active",
        description="Très bon état. Appelez-moi au 01 97 55 44 33 ou écrivez à moi@example.net",
        battery_health_pct=88,
        accessories=["charger"],
    )
    services.publish(listing)
    listing.refresh_from_db()
    other = make_listing(make_seller(2), imei="35" + "1" * 13, status="active", price_fcfa=280_000)
    sent: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if "audio/transcriptions" in str(request.url):
            sent.append(request.content.decode("utf-8", errors="ignore"))
            return httpx.Response(
                200, json={"text": "iPhone 12, appelez le 01 97 12 34 56, batterie 84"}
            )
        sent.append(request.content.decode())
        reply = {"choices": [{"message": {"content": json.dumps({})}}], "usage": {}}
        return httpx.Response(200, json=reply)  # an empty object: every feature falls back

    monkeypatch.setattr(
        ai_client, "http_client", lambda t: httpx.Client(transport=httpx.MockTransport(handler))
    )
    return listing, other, sent


def post(client, url, body):
    return client.post(url, body, content_type="application/json")


def test_no_feature_sends_personal_data_to_the_model(world, client):
    listing, other, sent = world
    # F1: a visitor pastes a phone number and an e-mail in the search box.
    post(
        client,
        "/api/ai/search/",
        {"query": "pc pour coder, appelez le 01 97 12 34 56 ou moi@example.net max 250k"},
    )
    # F2: the seller asks for a description of a listing that carries contact details.
    client.force_login(listing.seller)
    post(client, "/api/ai/describe/", {"listing_id": listing.pk})
    # F3: the dictation contains a phone number.
    client.post("/api/ai/voice/", {"audio": SimpleUploadedFile("a.webm", b"a" * 900, "audio/webm")})
    client.logout()
    # F4: question and history with personal data.
    post(
        client,
        "/api/ai/assistant/",
        {
            "listing_id": listing.pk,
            "question": "Je peux vous joindre au 01 97 12 34 56 ? Batterie ?",
            "history": [{"q": "mon mail moi@example.net", "a": "le vendeur Koffi Adjovi répond"}],
        },
    )
    # F5: comparison.
    post(client, "/api/ai/compare/", {"ids": [listing.pk, other.pk], "usage": "photo"})
    # F6: the risk signal runs while publishing (done in the fixture too).
    listing.status = "draft"
    listing.save()
    services.publish(listing)

    assert len(sent) >= 6, "every feature should have reached the model"
    for payload in sent:
        for secret in SECRETS:
            assert secret not in payload, f"{secret!r} leaked in a request to the model"
    assert AIRequestLog.objects.filter(feature__in=["search", "assistant", "compare"]).exists()


def test_every_prompt_has_a_version_and_forbids_inventing():
    files = sorted(prompts.PROMPT_DIR.glob("*.md"))
    assert {f.stem for f in files} >= {
        "search",
        "describe",
        "voice",
        "assistant",
        "compare",
        "risk",
    }
    for file in files:
        version, body = prompts.load(file.stem)
        assert version.isdigit(), file.name
        assert "invente" in body.lower(), f"{file.name} must forbid invented data"
        assert "emoji" in body.lower(), f"{file.name} must ask for a factual tone without emoji"
        assert "json" in body.lower()
