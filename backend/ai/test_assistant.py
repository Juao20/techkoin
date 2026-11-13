import json

import httpx
import pytest
from django.core.management import call_command

from marketplace.models import Listing
from pricing.services import recompute_listing
from trust.tests import make_listing, make_seller

from . import client as ai_client
from .fallback.assistant import answer
from .models import AIRequestLog


@pytest.fixture
def catalog(db):
    call_command("seed_catalog", verbosity=0)


def listing(n=1, **extra):
    fields = dict(
        status="active",
        battery_health_pct=86,
        ram_gb=4,
        accessories=["charger", "invoice"],
        warranty_months=3,
        replaced_parts=["none"],
        network_5g=True,
        battery_autonomy_h=None,
    )
    fields.update(extra)
    item = make_listing(make_seller(n), **fields)
    recompute_listing(item)
    return item


def ask(client, item, question, history=None):
    return client.post(
        "/api/ai/assistant/",
        {"listing_id": item.pk, "question": question, "history": history or []},
        content_type="application/json",
    )


def test_rules_answer_from_the_listing_data(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    item = listing()
    cases = {
        "La batterie tient combien ?": "86 %",
        "Il y a une garantie ?": "3 mois",
        "Y a-t-il une facture ?": "Une facture est fournie",
        "Avec quoi est-il livré ?": "chargeur",
        "Des pièces ont été remplacées ?": "aucune pièce",
        "Combien de RAM ?": "4 Go",
        "Il est compatible 5G ?": "5G",
        "Le compte iCloud est retiré ?": "retiré",
    }
    for question, expected in cases.items():
        body = ask(client, item, question).json()
        assert expected.lower() in body["answer"].lower(), question
        assert body["used_ai"] is False and body["information_missing"] is False


def test_usage_questions_use_the_scores(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    item = listing()
    score = item.usage_scores["photo"]
    body = ask(client, item, "Ça marche pour la photo ?").json()
    assert f"{score:g}/10" in body["answer"]
    heavy = ask(client, item, "Ça suffit pour Premiere Pro ?").json()
    assert "limitée sur un smartphone" in heavy["answer"] and "/10" in heavy["answer"]


def test_missing_information_is_admitted_and_offers_to_ask_the_seller(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    item = listing(battery_health_pct=None)
    body = ask(client, item, "La batterie tient combien ?").json()
    assert body["information_missing"] is True
    assert body["suggested_seller_question"] == "La batterie tient combien ?"
    assert "pas indiquée" in body["answer"]
    unknown = ask(client, item, "Est-ce qu'il supporte le Bluetooth 5 ?").json()
    assert unknown["information_missing"] is True


def test_price_question_uses_the_estimate_without_inventing(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    item = listing()
    body = ask(client, item, "C'est une bonne affaire ?").json()
    assert "Prix du marché estimé" in body["answer"]
    assert f"{item.estimate_mid:,}".replace(",", " ") in body["answer"]


def test_answers_are_cached_per_listing_version(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    item = listing()
    first = ask(client, item, "Il y a une garantie ?").json()
    assert ask(client, item, "Il y a une garantie ?").json() == first
    assert AIRequestLog.objects.filter(feature="assistant", cache_hit=True).count() == 1
    Listing.objects.filter(pk=item.pk).update(warranty_months=6)
    item.refresh_from_db()
    Listing.objects.get(pk=item.pk).save()  # bumps updated_at: the cached answer no longer applies
    assert "6 mois" in ask(client, item, "Il y a une garantie ?").json()["answer"]


def test_only_public_listings_and_valid_questions(catalog, client, settings):
    settings.GROQ_API_KEY = ""
    draft = listing(1, status="draft")
    assert ask(client, draft, "Garantie ?").status_code == 404
    live = listing(2, status="active")
    assert ask(client, live, " ").status_code == 400


def model_reply(payload):
    return httpx.Response(
        200, json={"choices": [{"message": {"content": json.dumps(payload)}}], "usage": {}}
    )


def fake(monkeypatch, *replies):
    queue = list(replies)
    sent = []

    def handler(request):
        sent.append(request.content.decode())
        return queue.pop(0)

    monkeypatch.setattr(
        ai_client, "http_client", lambda t: httpx.Client(transport=httpx.MockTransport(handler))
    )
    return sent


def test_model_answer_is_used_and_receives_only_listing_data(
    catalog, client, settings, monkeypatch
):
    settings.GROQ_API_KEY = "k"
    item = listing()
    sent = fake(
        monkeypatch,
        model_reply(
            {
                "answer": "La batterie est déclarée à 86 % de santé.",
                "information_missing": False,
                "suggested_seller_question": None,
            }
        ),
    )
    body = ask(client, item, "Et la batterie ?").json()
    assert body["used_ai"] is True and "86 %" in body["answer"]
    prompt = sent[0]
    assert "example.com" not in prompt and "+229" not in prompt and "490154203237518" not in prompt


def test_invented_figures_are_rejected(catalog, client, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    item = listing()
    bad = model_reply({"answer": "Elle tient 14 heures.", "information_missing": False})
    fake(monkeypatch, bad, bad)
    body = ask(client, item, "La batterie tient combien ?").json()
    assert body["used_ai"] is False and "86 %" in body["answer"]


def test_history_is_limited_to_five_and_cleaned(catalog, client, settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    item = listing()
    sent = fake(monkeypatch, model_reply({"answer": "Oui.", "information_missing": False}))
    history = [{"q": f"question {i}", "a": "réponse écrire à moi@example.com"} for i in range(8)]
    ask(client, item, "Et la garantie ?", history)
    prompt = sent[0]
    assert "question 7" in prompt and "question 2" not in prompt  # last five only
    assert "moi@example.com" not in prompt


def test_rules_module_is_pure(catalog):
    ctx = {"facts": {"stockage": "128 Go"}, "usage_scores": {}}
    assert answer("Quel stockage ?", ctx).answer == "Stockage : 128 Go."
