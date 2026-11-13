"""Side by side comparison, computed by Django (spec 10.2 F5).

Everything the interface shows, and everything the language model may cite, comes from here:
aligned specs, the best value per row, usage scores, position against the estimate and trust
signals. A deterministic verdict is also computed, so the feature works without a model.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Q

from marketplace.models import Listing

MIN_ITEMS, MAX_ITEMS = 2, 3
PC_USAGES = ("office", "study", "dev", "gaming", "creative", "battery")
MOBILE_USAGES = ("everyday", "photo", "gaming", "battery", "business")
GRADE_LABEL = {"A": "A, comme neuf", "B": "B, bon état", "C": "C, traces visibles"}
CONDITION_LABEL = {
    "new_sealed": "Neuf scellé",
    "new_open": "Neuf ouvert",
    "refurbished": "Reconditionné",
    "used": "Occasion",
}
USAGE_LABEL = {
    "office": "Bureautique",
    "study": "Études",
    "dev": "Développement",
    "gaming": "Jeux",
    "creative": "Photo et vidéo",
    "battery": "Autonomie",
    "everyday": "Quotidien",
    "photo": "Photo",
    "business": "Professionnel",
}


class CompareError(ValueError):
    pass


@dataclass(frozen=True)
class Row:
    key: str
    label: str
    values: list
    best: int | None = None
    group: str = "spec"

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "values": self.values,
            "best": self.best,
            "group": self.group,
        }


def usages_for(category: str) -> tuple[str, ...]:
    return PC_USAGES if category in ("laptop", "desktop") else MOBILE_USAGES


def load(ids: list[int]) -> list[Listing]:
    if not MIN_ITEMS <= len(set(ids)) <= MAX_ITEMS:
        raise CompareError(f"Choisissez entre {MIN_ITEMS} et {MAX_ITEMS} annonces à comparer.")
    found = {
        listing.pk: listing
        for listing in Listing.objects.filter(
            pk__in=ids, status__in=["active", "reserved", "sold"]
        ).select_related("shop", "seller", "processor", "gpu", "brand")
    }
    if len(found) != len(set(ids)):
        raise CompareError("Une des annonces n'est plus disponible.")
    listings = [found[i] for i in dict.fromkeys(ids)]
    if len({x.category for x in listings}) > 1:
        raise CompareError("Comparez des appareils de la même catégorie.")
    return listings


def _best(values: list, higher=True) -> int | None:
    scored = [(v, i) for i, v in enumerate(values) if isinstance(v, (int, float)) and v is not None]
    if len(scored) < 2:
        return None
    target = max(v for v, _ in scored) if higher else min(v for v, _ in scored)
    winners = [i for v, i in scored if v == target]
    return winners[0] if len(winners) == 1 else None  # a tie has no best


def _gap_pct(listing: Listing) -> int | None:
    """Price against the estimate, in %: negative when cheaper than the market."""
    if not listing.estimate_mid or listing.moderation_flags.get("estimate_indicative", True):
        return None
    return round((listing.price_fcfa / listing.estimate_mid - 1) * 100)


def _trusted(listing: Listing) -> bool:
    return bool(
        (listing.shop and listing.shop.is_verified) or listing.seller.identity_status == "verified"
    )


def table(listings: list[Listing]) -> list[Row]:
    def col(fn):
        return [fn(x) for x in listings]

    rows: list[Row] = []
    price = col(lambda x: x.price_fcfa)
    rows.append(Row("price", "Prix (FCFA)", price, _best(price, higher=False), "price"))
    gaps = col(_gap_pct)
    rows.append(
        Row("market_gap", "Écart avec le marché (%)", gaps, _best(gaps, higher=False), "price")
    )
    rows.append(
        Row("condition", "État", col(lambda x: CONDITION_LABEL.get(x.condition_type, "")), None)
    )
    grades = col(lambda x: GRADE_LABEL.get(x.grade, "-") if x.grade else "-")
    rows.append(Row("grade", "Note d'état", grades, None))
    ram = col(lambda x: x.ram_gb)
    rows.append(Row("ram", "Mémoire vive (Go)", ram, _best(ram)))
    storage = col(lambda x: x.storage_gb)
    rows.append(Row("storage", "Stockage (Go)", storage, _best(storage)))
    cpu = col(lambda x: x.processor.perf_score if x.processor else None)
    rows.append(
        Row(
            "cpu", "Processeur", col(lambda x: x.processor.name if x.processor else "-"), _best(cpu)
        )
    )
    if listings[0].category in ("laptop", "desktop"):
        gpu = col(lambda x: x.gpu.perf_score if x.gpu else None)
        rows.append(
            Row("gpu", "Carte graphique", col(lambda x: x.gpu.name if x.gpu else "-"), _best(gpu))
        )
    screen = col(lambda x: float(x.screen_size_in) if x.screen_size_in else None)
    rows.append(Row("screen", "Écran (pouces)", screen, None))
    battery = col(lambda x: x.battery_health_pct)
    if any(b is not None for b in battery):
        rows.append(Row("battery_health", "Santé de la batterie (%)", battery, _best(battery)))
    for usage in usages_for(listings[0].category):
        scores = col(lambda x, u=usage: (x.usage_scores or {}).get(u))
        rows.append(Row(f"usage_{usage}", USAGE_LABEL[usage], scores, _best(scores), "usage"))
    warranty = col(lambda x: x.warranty_months)
    rows.append(Row("warranty", "Garantie (mois)", warranty, _best(warranty), "trust"))
    rows.append(
        Row("invoice", "Facture", col(lambda x: "Oui" if x.has_invoice else "Non"), None, "trust")
    )
    rows.append(
        Row(
            "verified",
            "Vendeur vérifié",
            col(lambda x: "Oui" if _trusted(x) else "Non"),
            None,
            "trust",
        )
    )
    rows.append(
        Row(
            "parts",
            "Pièces remplacées",
            col(
                lambda x: (
                    "Aucune"
                    if x.replaced_parts in ([], ["none"])
                    else ", ".join(p for p in x.replaced_parts if p != "none")
                )
            ),
            None,
            "trust",
        )
    )
    return rows


def score(listing: Listing, usage: str | None, budget: int | None) -> tuple[float, dict]:
    """Deterministic ranking: usage fit 50 %, value for money 30 %, trust 20 %."""
    scores = listing.usage_scores or {}
    fit = scores.get(usage) if usage else (max(scores.values()) if scores else None)
    fit = 5.0 if fit is None else fit
    gap = _gap_pct(listing)
    value = (
        5.0 if gap is None else max(0.0, min(10.0, 5 - gap / 4))
    )  # 20 % cheaper: 10, 20 % dearer: 0
    trust = 4.0
    trust += 2.0 if _trusted(listing) else 0
    trust += 1.5 if listing.has_invoice else 0
    trust += 1.5 if listing.warranty_months else 0
    trust += 1.0 if listing.imei_status == "ok" else 0
    trust -= 2.0 if listing.replaced_parts not in ([], ["none"]) else 0
    trust = max(0.0, min(10.0, trust))
    total = 0.5 * fit + 0.3 * value + 0.2 * trust
    over_budget = bool(budget and listing.price_fcfa > budget)
    if over_budget:
        total -= 3.0
    return round(total, 2), {
        "fit": round(fit, 1),
        "value": round(value, 1),
        "trust": round(trust, 1),
        "over_budget": over_budget,
    }


def warnings(listing: Listing, budget: int | None) -> list[str]:
    out = []
    if budget and listing.price_fcfa > budget:
        out.append("Au-dessus du budget indiqué")
    if listing.grade == "C":
        out.append("Traces d'usage visibles (note C)")
    if listing.battery_health_pct and listing.battery_health_pct < 80:
        out.append(f"Batterie à {listing.battery_health_pct} %")
    if listing.replaced_parts not in ([], ["none"]):
        out.append("Pièces remplacées")
    gap = _gap_pct(listing)
    if gap is not None and gap >= 15:
        out.append("Prix au-dessus du marché")
    if not listing.has_invoice and not listing.warranty_months:
        out.append("Ni facture ni garantie")
    return out[:3]


def best_for(listing: Listing, others: list[Listing]) -> str:
    """The most distinctive strength of a listing against the others, in plain words."""
    if all(listing.price_fcfa <= o.price_fcfa for o in others):
        return "le prix le plus bas"
    scores = listing.usage_scores or {}
    leads = [
        u for u in scores if all(scores[u] > (o.usage_scores or {}).get(u, -1) for o in others)
    ]
    if leads:
        return f"{USAGE_LABEL[leads[0]].lower()}"
    gap = _gap_pct(listing)
    if gap is not None and all(gap < (_gap_pct(o) or 999) for o in others):
        return "le meilleur rapport qualité-prix"
    if listing.warranty_months and all(listing.warranty_months > o.warranty_months for o in others):
        return "la garantie la plus longue"
    return "un usage polyvalent"


def deterministic_verdict(listings: list[Listing], usage: str | None, budget: int | None) -> dict:
    ranked = sorted(listings, key=lambda x: score(x, usage, budget)[0], reverse=True)
    winner = ranked[0]
    totals = {x.pk: score(x, usage, budget) for x in listings}
    reasons = []
    w_scores = totals[winner.pk][1]
    if usage:
        reasons.append(f"Meilleur score pour {USAGE_LABEL[usage].lower()} : {w_scores['fit']:g}/10")
    gap = _gap_pct(winner)
    if gap is not None:
        reasons.append(
            f"Prix {abs(gap)} % {'sous' if gap <= 0 else 'au-dessus de'} l'estimation du marché"
        )
    if winner.warranty_months:
        reasons.append(f"Garantie de {winner.warranty_months} mois")
    if _trusted(winner):
        reasons.append("Vendeur vérifié")
    others = [x for x in listings if x.pk != winner.pk]
    summary = (
        f"{winner.title} ressort en premier"
        + (f" pour {USAGE_LABEL[usage].lower()}" if usage else "")
        + ", en tenant compte du prix, de l'état et de la confiance."
    )
    return {
        "winner_listing_id": winner.pk,
        "summary": summary,
        "reasons": reasons[:4],
        "warnings": warnings(winner, budget),
        "per_listing": [
            {
                "listing_id": x.pk,
                "best_for": best_for(x, [o for o in listings if o.pk != x.pk]),
                "verdict_line": (
                    f"Note globale {totals[x.pk][0]:g}/10"
                    + (" · au-dessus du budget" if totals[x.pk][1]["over_budget"] else "")
                ),
            }
            for x in listings
        ],
        "_others": [o.pk for o in others],
    }


def alternatives(listing: Listing, n: int = 2) -> list[Listing]:
    """Two alternatives picked by Django: same category, price within 20 %, close usage scores."""
    low, high = int(listing.price_fcfa * 0.8), int(listing.price_fcfa * 1.2)
    qs = (
        Listing.objects.filter(
            category=listing.category,
            status="active",
            price_fcfa__gte=low,
            price_fcfa__lte=high,
        )
        .exclude(pk=listing.pk)
        .filter(~Q(device_model=listing.device_model) | Q(device_model__isnull=True))
        .select_related("shop", "seller", "processor", "gpu", "brand")[:60]
    )
    mine = listing.usage_scores or {}

    def distance(other: Listing) -> float:
        theirs = other.usage_scores or {}
        keys = set(mine) & set(theirs)
        return sum(abs(mine[k] - theirs[k]) for k in keys) / max(len(keys), 1)

    return sorted(qs, key=distance)[:n]
