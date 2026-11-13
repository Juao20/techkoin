"""P5, « Discuter avec ses chiffres ».

With a Groq key the model chooses among the predefined functions of `tools.py`. Without one (or
when the model fails, or states a number the functions never returned) a keyword reader picks the
function and a template words the answer, so the feature always works.
"""

from __future__ import annotations

import re
import unicodedata

from ai import client, privacy, prompts

from . import llm, tools

MAX_QUESTION = 300
STOPWORDS = set(
    """combien je vous nous de des du la le les un une sur mes mon ma ce cet cette ces est ai j
    jai quel quels quelle quelles ont a t il y en et au aux dans pour par que qui plus moins mois
    semaine trimestre dernier derniere dernieres derniers depuis jours jour annonces annonce
    produits produit boutique nombre total avons eu recu recus fait vendu vendus vendue vendues
    """.split()
)
METRIC_WORDS = {
    "contacts": ("contact", "whatsapp", "appel", "numero"),
    "views": ("vue", "visite", "consult"),
    "favorites": ("favori",),
    "sales": ("vente", "vendu", "vendre"),
}
CATEGORY_WORDS = {
    "smartphone": ("smartphone", "telephone"),
    "tablet": ("tablette",),
    "laptop": ("portable", "laptop"),
    "desktop": ("fixe", "tour"),
}
PERIOD_LABEL = {
    "today": "aujourd'hui",
    "7d": "sur les 7 derniers jours",
    "30d": "sur les 30 derniers jours",
    "90d": "sur les 90 derniers jours",
    "this_week": "cette semaine",
    "last_week": "la semaine précédente",
    "this_month": "ces 30 derniers jours",
    "last_month": "les 30 jours d'avant",
}
METRIC_LABEL = {"views": "vues", "contacts": "contacts", "favorites": "favoris", "sales": "ventes"}


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _period(q: str) -> str:
    if "trimestre" in q or "90" in q:
        return "90d"
    if "semaine" in q:
        return "this_week"
    if "aujourd" in q:
        return "today"
    return "30d"


def _metric(q: str) -> str:
    for metric, words in METRIC_WORDS.items():
        if any(w in q for w in words):
            return metric
    return "views"


def _model_words(q: str, extra_skip: set[str]) -> str | None:
    words = [
        w
        for w in re.findall(r"[a-z0-9]+", q)
        if w not in STOPWORDS and not any(w.startswith(stem) for stem in extra_skip)
    ]
    return " ".join(words) or None


def plan(question: str) -> tuple[str, dict]:
    """Keyword reading of the question: the function to call and its arguments."""
    q = fold(question)
    metric = _metric(q)
    skip = {w for ws in METRIC_WORDS.values() for w in ws}
    skip |= {w for ws in CATEGORY_WORDS.values() for w in ws}
    skip |= {"meilleur", "meilleurs", "top", "compar", "evolution", "prix", "demande", "cherch"}
    category = next((c for c, ws in CATEGORY_WORDS.items() if any(w in q for w in ws)), None)
    if re.search(r"meilleur|top|plus (vu|consult|contact|populaire)|le plus", q):
        return "top_listings", {"period": _period(q), "metric": metric, "limit": 5}
    if re.search(r"compar|par rapport|evolu|progress|baisse|hausse", q):
        if "mois" in q:
            return "compare_periods", {
                "metric": metric,
                "period_a": "this_month",
                "period_b": "last_month",
            }
        return "compare_periods", {
            "metric": metric,
            "period_a": "this_week",
            "period_b": "last_week",
        }
    if re.search(r"prix|trop cher|tarif|estimation", q):
        return "price_position", {}
    if re.search(r"demande|cherch|recherch", q):
        words = _model_words(q, skip | {"ville"})
        return "demand_for", {"model_or_family": words or ""}
    args: dict = {"period": _period(q), "metric": metric}
    if category:
        args["category"] = category
    model = _model_words(q, skip)
    if model:
        args["model"] = model
    return "get_stats", args


def _money(value) -> str:
    return f"{int(value):,}".replace(",", " ") + " FCFA"


def render(name: str, result: dict) -> str:
    """Template answer from one function result."""
    if "error" in result:
        return (
            "Je n'ai pas pu calculer cela. Essayez par exemple : « Combien de contacts "
            "ai-je eu sur les iPhone ce mois ? »"
        )
    if name == "get_stats":
        what = METRIC_LABEL[result["metric"]]
        scope = f" sur « {result['model']} »" if result.get("model") else ""
        return f"{result['value']} {what}{scope} {PERIOD_LABEL[result['period']]}."
    if name == "top_listings":
        rows = [r for r in result["listings"] if r["value"] > 0]
        if not rows:
            return "Aucune annonce n'a encore de chiffres sur cette période."
        lines = ", ".join(f"{r['title']} ({r['value']})" for r in rows[:3])
        return f"En tête sur {METRIC_LABEL[result['metric']]} : {lines}."
    if name == "compare_periods":
        change = result["change_pct"]
        trend = "" if change is None else f", soit {'+' if change > 0 else ''}{change} %"
        return (
            f"{result['value_a']} {METRIC_LABEL[result['metric']]} "
            f"{PERIOD_LABEL[result['period_a']]} contre {result['value_b']} "
            f"{PERIOD_LABEL[result['period_b']]}{trend}."
        )
    if name == "price_position":
        items = [i for i in result["listings"] if i["action"] in ("lower", "raise")]
        if not items:
            return "Vos prix sont cohérents avec les estimations du marché."
        i = items[0]
        verb = "baisser" if i["action"] == "lower" else "relever"
        return (
            f"« {i['title']} » est affichée {_money(i['price_fcfa'])} pour une estimation de "
            f"{_money(i['estimate_fcfa'])} : conseil, {verb} à {_money(i['advised_price_fcfa'])}."
        )
    if name == "demand_for":
        if result.get("too_few_searches"):
            return "Moins de 10 recherches sur ce modèle : le chiffre n'est pas communiqué."
        return (
            f"{result['searches_30d']} recherches sur 30 jours pour "
            f"« {result['model_or_family']} », dont "
            f"{result['searches_without_result']} sans résultat ; "
            f"{result['listings_available']} annonce(s) disponible(s), "
            f"dont {result['my_listings']} chez vous."
        )
    return "Question non prise en charge."


def answer(shop, question: str) -> dict:
    question = privacy.scrub_text(question.strip())[:MAX_QUESTION]
    run = lambda name, args: tools.run(shop, name, args)  # noqa: E731
    _, system = prompts.load("insights_chat")
    outcome = client.chat_with_tools(
        "insights_chat", system, question, tools.TOOLS, run, user=shop.owner, shop=shop
    )
    if outcome is not None:
        text, calls = outcome
        if calls and not llm.invented_numbers([text], [c["result"] for c in calls] + [question]):
            return {"answer": text, "used_ai": True, "calls": calls}
        # No function was called, or the text states numbers nobody gave it: do not show it.
    name, arguments = plan(question)
    result = run(name, arguments)
    return {
        "answer": render(name, result),
        "used_ai": False,
        "calls": [{"name": name, "arguments": arguments, "result": result}],
    }
