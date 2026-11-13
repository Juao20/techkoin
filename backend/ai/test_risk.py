import json

import httpx
import pytest
from django.core.management import call_command

from marketplace import services
from trust.tests import make_listing, make_seller

from . import client as ai_client
from .models import AIRequestLog
from .risk import signal


@pytest.fixture
def catalog(db):
    call_command("seed_catalog", verbosity=0)


def groq(monkeypatch, payload):
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        if isinstance(payload, Exception):
            raise payload
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(payload)}}], "usage": {}}
        )

    monkeypatch.setattr(
        ai_client, "http_client", lambda t: httpx.Client(transport=httpx.MockTransport(handler))
    )
    return sent


def test_without_a_key_the_signal_is_zero_and_rules_still_decide(catalog, settings):
    settings.GROQ_API_KEY = ""
    listing = make_listing(make_seller(1), description="Appareil en bon état, rencontre possible.")
    assert signal(listing).risk == 0
    services.publish(listing)
    listing.refresh_from_db()
    assert listing.status == "active" and "ai_signal" not in listing.moderation_flags["risk_rules"]


def test_the_signal_adds_points_but_never_blocks_alone(catalog, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    groq(monkeypatch, {"risk": 25, "signals": ["Demande d'acompte avant la rencontre"]})
    listing = make_listing(make_seller(1), description="Dernier jour, envoyez un acompte vite")
    services.publish(listing)
    listing.refresh_from_db()
    assert listing.moderation_flags["risk_rules"]["ai_signal"] == 25
    assert listing.moderation_flags["ai_signals"] == ["Demande d'acompte avant la rencontre"]
    assert listing.risk_score == 25 and listing.status == "active"  # 25 < 40


def test_the_signal_adds_to_other_rules(catalog, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    groq(monkeypatch, {"risk": 20, "signals": ["Incohérence"]})
    listing = make_listing(
        make_seller(1), description="Paiement avant la rencontre, appelez le 01 97 55 44 33"
    )
    services.publish(listing)
    listing.refresh_from_db()
    assert listing.risk_score == 30 + 20 + 20  # phrase + contact + model signal
    assert listing.status == "pending_review"


def test_out_of_range_or_broken_answers_fall_back_to_zero(catalog, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    groq(monkeypatch, {"risk": 80, "signals": []})  # above 25: invalid for the schema
    listing = make_listing(make_seller(1), description="Texte normal d'un vendeur")
    assert signal(listing).risk == 0
    assert AIRequestLog.objects.filter(feature="risk", fallback_used=True).exists()


def test_phone_numbers_in_the_text_never_reach_the_model(catalog, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    sent = groq(monkeypatch, {"risk": 0, "signals": []})
    listing = make_listing(make_seller(1), description="Appelez-moi au 01 97 55 44 33 ou a@b.co")
    signal(listing)
    blob = json.dumps(sent, ensure_ascii=False)
    assert "55 44 33" not in blob and "a@b.co" not in blob
    assert "contact retiré" in blob


def test_an_unexpected_failure_never_breaks_publication(catalog, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    monkeypatch.setattr(
        ai_client, "complete", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    listing = make_listing(make_seller(1))
    services.publish(listing)
    listing.refresh_from_db()
    assert listing.status == "active"
