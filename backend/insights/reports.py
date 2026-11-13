"""P4, « Rapport hebdomadaire »: figures of the last 7 days, written by the model, sent by e-mail.

Every number comes from `analytics.stats`; the model only words the summary and the three
priority actions, and its text is rejected when it contains a number it was not given.
"""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from accounts.models import Shop
from analytics import stats

from . import demand, dormant, llm, notifiers, pricing_advice
from .models import WeeklyReport
from .schemas import ReportText


def money(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " FCFA"


def signed(pct) -> str:
    return "" if pct is None else f" ({'+' if pct > 0 else ''}{pct} % sur la semaine précédente)"


def figures(shop: Shop) -> dict:
    """Everything the report states, computed once and stored with it."""
    now, before = stats.totals(shop, 7), stats.totals(shop, 7, ago=1)
    rows = stats.listing_rows(shop, 7, status=("active", "reserved", "sold"))
    best = sorted(rows, key=lambda r: (-r["contacts"], -r["views"]))[:3]
    lower = [r for r in pricing_advice.rows(shop, 30) if r["action"] == "lower"]
    sleepers = dormant.diagnose(shop, 30, with_fixes=False)["rows"]
    gaps = [r for r in demand.radar(shop, 7)["rows"] if r["my_supply"] == 0][:1]
    return {
        "views": now["views"],
        "contacts": now["contacts"],
        "favorites": now["favorites"],
        "sales": now["sales"],
        "revenue_fcfa": now["revenue_fcfa"],
        "change": {k: stats.change_pct(now[k], before[k]) for k in ("views", "contacts", "sales")},
        "best_listings": [
            {"title": r["title"], "views": r["views"], "contacts": r["contacts"]}
            for r in best
            if r["views"] or r["contacts"]
        ],
        "listings_to_reprice": len(lower),
        "dormant_listings": len(sleepers),
        "unmet_demand": [
            {"label": r["label"], "searches": r["searches"], "city": r["city"]} for r in gaps
        ],
    }


def deterministic_actions(data: dict) -> list[str]:
    actions = []
    if data["best_listings"]:
        top = data["best_listings"][0]
        actions.append(
            f"Mettez en avant « {top['title']} » : {top['contacts']} contact(s) "
            f"pour {top['views']} vue(s) cette semaine."
        )
    if data["listings_to_reprice"]:
        actions.append(
            f"Revoyez le prix de {data['listings_to_reprice']} annonce(s) "
            "au-dessus de l'estimation du marché."
        )
    if data["dormant_listings"]:
        actions.append(
            f"Améliorez {data['dormant_listings']} annonce(s) en ligne depuis plus de 14 jours "
            "sans contacts suffisants."
        )
    if data["unmet_demand"]:
        gap = data["unmet_demand"][0]
        actions.append(
            f"Cherchez des « {gap['label']} » à vendre : {gap['searches']} recherches "
            "cette semaine et aucune annonce chez vous."
        )
    if not actions:
        actions.append("Publiez de nouvelles annonces pour gagner des vues.")
    return actions[:3]


def fallback_text(data: dict) -> ReportText:
    c = data["change"]
    summary = (
        f"Cette semaine, votre boutique a reçu {data['views']} vue(s){signed(c['views'])} "
        f"et {data['contacts']} contact(s){signed(c['contacts'])}. "
        f"{data['sales']} vente(s) conclue(s), pour {money(data['revenue_fcfa'])}."
    )
    return ReportText(summary=summary, actions=deterministic_actions(data))


def build(shop: Shop, now=None) -> WeeklyReport:
    """Create (or refresh) the report of the 7 days that end now."""
    now = now or timezone.now()
    start, end = stats.window(7)
    data = figures(shop)
    text, used_ai = llm.write(
        "insights_report",
        "insights_report",
        data,
        ReportText,
        lambda: fallback_text(data),
        lambda v: [v.summary, *v.actions],
        shop=shop,
    )
    report, _ = WeeklyReport.objects.update_or_create(
        shop=shop,
        period_start=start.replace(minute=0, second=0, microsecond=0),
        defaults={
            "period_end": end,
            "figures": data,
            "summary": text.summary,
            "actions": text.actions,
            "used_ai": used_ai,
        },
    )
    return report


def email_body(report: WeeklyReport) -> str:
    actions = "\n".join(f"{i}. {a}" for i, a in enumerate(report.actions, 1))
    return (
        f"Bonjour,\n\nVoici le rapport de la semaine pour {report.shop.name}.\n\n"
        f"{report.summary}\n\nTrois actions pour la semaine qui vient :\n{actions}\n\n"
        f"Le détail est dans votre tableau de bord : {settings.SITE_URL}/pro/analyse\n\n"
        "L'équipe TechKoin"
    )


def send(report: WeeklyReport) -> bool:
    subject = f"Rapport hebdomadaire de {report.shop.name}"
    sent = any(n.send(report.shop, subject, email_body(report)) for n in notifiers.NOTIFIERS)
    if sent:
        report.emailed_at = timezone.now()
        report.save(update_fields=["emailed_at", "updated_at"])
    return sent


def run_weekly(now=None) -> dict:
    """Every Pro shop gets its report; one that was already e-mailed this week is left alone."""
    built = sent = 0
    for shop in Shop.objects.filter(plan=Shop.Plan.PRO).select_related("owner"):
        if not shop.is_pro:
            continue
        report = build(shop, now)
        built += 1
        if report.emailed_at is None and send(report):
            sent += 1
    return {"reports": built, "emails": sent}
