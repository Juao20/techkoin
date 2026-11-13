"""P4 weekly report, P5 chat with tool calling, P6 bulk optimisation, P7 competition."""

import json

import httpx
import pytest
from django.core import mail
from django.core.management import call_command
from rest_framework.test import APIClient

from ai import client as ai_client
from marketplace.models import Listing

from . import bulk, chat, competition, reports, tools
from .factories import add_events, add_listing, make_shop
from .models import WeeklyReport

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def catalog():
    call_command("seed_catalog", verbosity=0)


def as_user(shop) -> APIClient:
    c = APIClient()
    c.force_login(shop.owner)
    return c


def fake_groq(monkeypatch, *replies):
    queue, seen = list(replies), []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=queue.pop(0))

    monkeypatch.setattr(
        ai_client, "http_client", lambda t: httpx.Client(transport=httpx.MockTransport(handler))
    )
    return seen


def say(content=None, tool_calls=None):
    message = {"content": content or ""}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"choices": [{"message": message}], "usage": {}}


def call(name, **arguments):
    return {
        "id": "c1",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


# ------------------------------------------------------------------ P4


def week_of_activity():
    shop = make_shop()
    best, other = add_listing(shop), add_listing(shop, "apple-iphone-12")
    add_events("listing_view", 20, listing=best, shop=shop, days_ago=2)
    add_events("whatsapp_click", 5, listing=best, shop=shop, days_ago=2)
    add_events("listing_view", 8, listing=other, shop=shop, days_ago=3)
    add_events("listing_view", 10, listing=best, shop=shop, days_ago=9)
    return shop, best


def test_the_report_states_computed_figures():
    shop, best = week_of_activity()
    report = reports.build(shop)
    assert (report.figures["views"], report.figures["contacts"]) == (28, 5)
    assert report.figures["change"]["views"] == 180
    assert report.figures["best_listings"][0]["title"] == best.title
    assert "28 vue(s)" in report.summary and "5 contact(s)" in report.summary
    assert 1 <= len(report.actions) <= 3 and report.used_ai is False


def test_building_twice_in_the_same_hour_keeps_one_report():
    shop, _ = week_of_activity()
    reports.build(shop)
    reports.build(shop)
    assert WeeklyReport.objects.filter(shop=shop).count() == 1


def test_weekly_run_emails_each_pro_shop_once():
    pro, _ = week_of_activity()
    free = make_shop(2, plan="free")
    add_listing(free)
    first = reports.run_weekly()
    assert first == {"reports": 1, "emails": 1}
    assert len(mail.outbox) == 1 and mail.outbox[0].to == [pro.owner.email]
    assert "Rapport hebdomadaire" in mail.outbox[0].subject and "28 vue" in mail.outbox[0].body
    assert reports.run_weekly()["emails"] == 0  # already sent this week
    assert not WeeklyReport.objects.filter(shop=free).exists()


def test_the_command_runs():
    week_of_activity()
    call_command("send_weekly_reports", verbosity=0)
    assert len(mail.outbox) == 1


def test_report_endpoints_belong_to_the_shop():
    shop, _ = week_of_activity()
    c = as_user(shop)
    made = c.post("/api/insights/reports/", {}, format="json")
    assert made.status_code == 201 and made.json()["figures"]["views"] == 28
    listing = c.get("/api/insights/reports/").json()["results"]
    assert len(listing) == 1
    assert c.get(f"/api/insights/reports/{listing[0]['id']}/").status_code == 200
    stranger = as_user(make_shop(2))
    assert stranger.get(f"/api/insights/reports/{listing[0]['id']}/").status_code == 404


def test_report_text_with_an_invented_number_is_replaced(settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    shop, _ = week_of_activity()
    lie = {"summary": "Vous avez eu 9999 vues cette semaine.", "actions": ["Faites mieux."]}
    fake_groq(monkeypatch, say(json.dumps(lie)), say(json.dumps(lie)))
    report = reports.build(shop)
    assert report.used_ai is False and "9999" not in report.summary


def test_a_valid_report_text_from_the_model_is_kept(settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    shop, _ = week_of_activity()
    good = {
        "summary": "28 vues et 5 contacts cette semaine.",
        "actions": ["Mettez en avant votre meilleure annonce."],
    }
    seen = fake_groq(monkeypatch, say(json.dumps(good)))
    report = reports.build(shop)
    assert report.used_ai is True and report.summary == good["summary"]
    payload = json.dumps(seen)
    assert shop.owner.email not in payload and shop.name not in payload


# ------------------------------------------------------------------ P5


def test_chat_without_a_key_answers_from_the_right_function():
    shop = make_shop()
    phones = add_listing(shop)
    laptop = add_listing(shop, "apple-macbook-air-m1")
    add_events("whatsapp_click", 7, listing=phones, shop=shop, days_ago=3)
    add_events("whatsapp_click", 4, listing=laptop, shop=shop, days_ago=3)
    rival = make_shop(2)
    add_events("whatsapp_click", 50, listing=add_listing(rival), shop=rival, days_ago=3)
    out = chat.answer(shop, "Combien de contacts sur les iPhone ce mois ?")
    call_ = out["calls"][0]
    assert call_["name"] == "get_stats" and call_["arguments"]["metric"] == "contacts"
    assert call_["result"]["value"] == 7  # only this shop's iPhone contacts
    assert out["answer"].startswith("7 contacts") and out["used_ai"] is False


@pytest.mark.parametrize(
    "question,function",
    [
        ("Quelles sont mes annonces les plus vues ?", "top_listings"),
        ("Compare mes vues avec la semaine dernière", "compare_periods"),
        ("Mes prix sont-ils trop chers ?", "price_position"),
        ("Quelle est la demande pour le macbook ?", "demand_for"),
        ("Combien de favoris cette semaine ?", "get_stats"),
    ],
)
def test_chat_reads_the_intent_of_the_question(question, function):
    shop = make_shop()
    assert chat.answer(shop, question)["calls"][0]["name"] == function


def test_the_tools_are_bound_to_the_shop_and_refuse_bad_input():
    shop, other = make_shop(1), make_shop(2)
    theirs = add_listing(other)
    add_events("listing_view", 30, listing=theirs, shop=other, days_ago=1)
    assert tools.run(shop, "get_stats", {"period": "30d", "metric": "views"})["value"] == 0
    assert "error" in tools.run(shop, "get_stats", {"period": "forever", "metric": "views"})
    assert "error" in tools.run(shop, "price_position", {"listing_id": theirs.pk})
    assert "error" in tools.run(shop, "run_sql", {"query": "select * from accounts_user"})
    assert "error" in tools.run(
        shop, "get_stats", {"period": "7d", "metric": "views", "category": "x"}
    )


def test_demand_for_hides_small_counts():
    shop = make_shop()
    add_events("search", 9, query_text="macbook m1", filters={"q": "macbook m1"})
    assert tools.run(shop, "demand_for", {"model_or_family": "macbook"})["too_few_searches"]
    add_events("search", 3, query_text="macbook m1", filters={"q": "macbook m1"})
    result = tools.run(shop, "demand_for", {"model_or_family": "macbook"})
    assert result["searches_30d"] == 12


def test_chat_with_the_model_runs_the_requested_function(settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    shop = make_shop()
    listing = add_listing(shop)
    add_events("whatsapp_click", 7, listing=listing, shop=shop, days_ago=2)
    seen = fake_groq(
        monkeypatch,
        say(tool_calls=[call("get_stats", period="30d", metric="contacts")]),
        say("Vous avez reçu 7 contacts sur les 30 derniers jours."),
    )
    out = chat.answer(shop, "Combien de contacts ce mois ?")
    assert out["used_ai"] is True and "7 contacts" in out["answer"]
    assert out["calls"][0]["result"]["value"] == 7
    assert seen[0]["tools"] and "run_sql" not in json.dumps(seen[0]["tools"])
    assert any(m.get("role") == "tool" for m in seen[1]["messages"])


def test_chat_never_shows_a_number_the_functions_did_not_return(settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    shop = make_shop()
    add_events("whatsapp_click", 7, listing=add_listing(shop), shop=shop, days_ago=2)
    fake_groq(
        monkeypatch,
        say(tool_calls=[call("get_stats", period="30d", metric="contacts")]),
        say("Vous avez reçu 4321 contacts."),
    )
    out = chat.answer(shop, "Combien de contacts ce mois ?")
    assert out["used_ai"] is False and "4321" not in out["answer"] and "7 contacts" in out["answer"]


def test_chat_endpoint_and_contact_details_in_the_question(settings, monkeypatch):
    settings.GROQ_API_KEY = "k"
    shop = make_shop()
    seen = fake_groq(monkeypatch, say("Je ne sais pas."))
    r = as_user(shop).post(
        "/api/insights/chat/",
        {"question": "Rappelle-moi au 01 97 12 34 56 ou jean@mail.com : combien de vues ?"},
        format="json",
    )
    assert r.status_code == 200
    sent = json.dumps(seen)
    assert "jean@mail.com" not in sent and "97 12 34 56" not in sent
    assert (
        as_user(shop).post("/api/insights/chat/", {"question": "?"}, format="json").status_code
        == 400
    )


# ------------------------------------------------------------------ P6


def test_bulk_proposals_write_nothing_until_applied():
    shop = make_shop()
    a, b = add_listing(shop, description="vieux texte"), add_listing(shop)
    items = bulk.propose(shop, [a.pk, b.pk])
    assert [i["listing_id"] for i in items] == [a.pk, b.pk]
    assert items[0]["before"]["description"] == "vieux texte" and items[0]["after"]["title"]
    a.refresh_from_db()
    assert a.description == "vieux texte"
    done = bulk.apply(
        shop, [{"listing_id": a.pk, "title": "Nouveau titre", "description": "Nouveau"}]
    )
    assert done == [a.pk]
    a.refresh_from_db(), b.refresh_from_db()
    assert (a.title, a.description) == ("Nouveau titre", "Nouveau")
    assert "nouveau titre" in a.search_text and b.title != "Nouveau titre"


def test_bulk_limits_and_ownership():
    shop, other = make_shop(1), make_shop(2)
    mine, theirs = add_listing(shop), add_listing(other)
    with pytest.raises(bulk.BulkError):
        bulk.propose(shop, [])
    with pytest.raises(bulk.BulkError):
        bulk.propose(shop, list(range(1, 52)))
    with pytest.raises(bulk.BulkError):
        bulk.propose(shop, [mine.pk, theirs.pk])
    with pytest.raises(bulk.BulkError):
        bulk.apply(shop, [{"listing_id": theirs.pk, "title": "x", "description": "y"}])
    with pytest.raises(bulk.BulkError):
        bulk.apply(shop, [{"listing_id": mine.pk, "title": "", "description": "y"}])
    sold = add_listing(shop, status="sold")
    with pytest.raises(bulk.BulkError):
        bulk.propose(shop, [sold.pk])


def test_bulk_endpoints():
    shop = make_shop()
    ids = [add_listing(shop).pk for _ in range(3)]
    c = as_user(shop)
    r = c.post("/api/insights/bulk-optimize/", {"listing_ids": ids}, format="json")
    assert r.status_code == 200 and len(r.json()["items"]) == 3
    accepted = [{"listing_id": i["listing_id"], **i["after"]} for i in r.json()["items"][:2]]
    done = c.post("/api/insights/bulk-optimize/apply/", {"items": accepted}, format="json")
    assert done.status_code == 200 and len(done.json()["applied"]) == 2
    bad = c.post("/api/insights/bulk-optimize/", {"listing_ids": []}, format="json")
    assert bad.status_code == 400 and bad.json()["code"] == "invalid_selection"


# ------------------------------------------------------------------ P7


def test_the_three_closest_rivals_are_other_sellers_of_the_same_kind():
    shop, rival_shop = make_shop(1), make_shop(2)
    mine = add_listing(shop, price=300_000)
    same_model = [add_listing(rival_shop, price=p) for p in (310_000, 280_000, 360_000)]
    add_listing(rival_shop, "apple-iphone-12", price=300_000)
    add_listing(rival_shop, price=900_000)  # far too expensive to compete
    add_listing(rival_shop, "apple-macbook-air-m1", price=300_000)  # another category
    add_listing(shop, price=300_000)  # same shop: not a rival
    found = competition.closest(mine)
    assert [x.pk for x in found] == [same_model[0].pk, same_model[1].pk, same_model[2].pk]


def test_competition_explains_what_rivals_do_better():
    shop, rival_shop = make_shop(1), make_shop(2)
    mine = add_listing(shop, price=330_000, warranty_months=0)
    add_listing(rival_shop, price=300_000, warranty_months=6, accessories=["charger", "box"])
    body = as_user(shop).get(f"/api/insights/competition/{mine.pk}/").json()
    kinds = {a["kind"] for a in body["actions"]}
    assert {"price", "warranty", "accessories"} <= kinds
    assert "30 000" in body["why_them"] and len(body["competitors"]) == 1
    assert body["competitors"][0]["shop"] == rival_shop.name


def test_competition_without_rivals_says_so_and_refuses_foreign_listings():
    shop, other = make_shop(1), make_shop(2)
    alone = add_listing(shop)
    c = as_user(shop)
    assert c.get(f"/api/insights/competition/{alone.pk}/").json()["competitors"] == []
    assert c.get(f"/api/insights/competition/{add_listing(other).pk}/").status_code == 404
    assert Listing.objects.count() == 2
