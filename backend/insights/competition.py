"""P7, « Comparer mon annonce à la concurrence »: the 3 closest rival listings and why a buyer
might pick them. The comparison is computed here; the model only words it, from the same facts."""

from __future__ import annotations

from marketplace.models import Listing

from . import llm
from .schemas import CompetitionAnswer

ACCESSORY = {
    "charger": "chargeur",
    "box": "boîte d'origine",
    "cable": "câble",
    "case": "coque",
    "earphones": "écouteurs",
    "invoice": "facture",
}


def closest(listing: Listing, n: int = 3) -> list[Listing]:
    """Same category, other sellers, price within 30 %, same model first, then closest price."""
    low, high = int(listing.price_fcfa * 0.7), int(listing.price_fcfa * 1.3)
    qs = (
        Listing.objects.filter(
            category=listing.category,
            status=Listing.Status.ACTIVE,
            price_fcfa__gte=low,
            price_fcfa__lte=high,
        )
        .exclude(shop=listing.shop)
        .exclude(seller=listing.seller)
        .select_related("shop", "device_model")
        .prefetch_related("photos")[:80]
    )
    mine = listing.usage_scores or {}

    def usage_gap(other: Listing) -> float:
        theirs = other.usage_scores or {}
        keys = set(mine) & set(theirs)
        return sum(abs(mine[k] - theirs[k]) for k in keys) / max(len(keys), 1)

    def rank(other: Listing):
        same_model = listing.device_model_id and other.device_model_id == listing.device_model_id
        return (
            0 if same_model else 1,
            abs(other.price_fcfa - listing.price_fcfa) / max(listing.price_fcfa, 1),
            usage_gap(other),
            other.pk,
        )

    return sorted(qs, key=rank)[:n]


def facts(listing: Listing) -> dict:
    gap = None
    if listing.estimate_mid:
        gap = round((listing.price_fcfa - listing.estimate_mid) * 100 / listing.estimate_mid)
    return {
        "id": listing.pk,
        "titre": listing.title,
        "prix_fcfa": listing.price_fcfa,
        "ecart_estimation_pct": gap,
        "badge_prix": listing.price_badge or None,
        "etat": listing.grade or listing.condition_type,
        "garantie_mois": listing.warranty_months,
        "accessoires": [ACCESSORY[a] for a in listing.accessories if a in ACCESSORY],
        "photos": len(listing.photos.all()),
        "sante_batterie_pct": listing.battery_health_pct,
        "negociable": listing.negotiable,
        "paiement_securise": listing.accepts_secure_payment,
    }


def deterministic(mine: dict, rivals: list[dict]) -> CompetitionAnswer:
    reasons, actions = [], []
    cheaper = [r for r in rivals if r["prix_fcfa"] < mine["prix_fcfa"]]
    if cheaper:
        best = min(cheaper, key=lambda r: r["prix_fcfa"])
        diff = mine["prix_fcfa"] - best["prix_fcfa"]
        reasons.append(f"une concurrente est {diff:,} FCFA moins chère".replace(",", " "))
        lowest = f"{best['prix_fcfa']:,}".replace(",", " ")
        actions.append(
            {"kind": "price", "text": f"Alignez votre prix : la moins chère est à {lowest} FCFA."}
        )
    longest = max(rivals, key=lambda r: r["garantie_mois"])
    if longest["garantie_mois"] > mine["garantie_mois"]:
        reasons.append(f"une concurrente offre {longest['garantie_mois']} mois de garantie")
        months = longest["garantie_mois"]
        actions.append(
            {
                "kind": "warranty",
                "text": f"Proposez une garantie : une concurrente offre {months} mois.",
            }
        )
    most = max(rivals, key=lambda r: r["photos"])
    if most["photos"] > mine["photos"]:
        reasons.append(f"une concurrente montre {most['photos']} photos contre {mine['photos']}")
        text = f"Ajoutez des photos : {mine['photos']} chez vous, {most['photos']} ailleurs."
        actions.append({"kind": "photos", "text": text})
    extra = {a for r in rivals for a in r["accessoires"]} - set(mine["accessoires"])
    if extra:
        names = ", ".join(sorted(extra)[:3])
        reasons.append(f"des concurrentes précisent : {names}")
        actions.append(
            {
                "kind": "accessories",
                "text": f"Indiquez les accessoires fournis ({names}) si vous les avez.",
            }
        )
    if not reasons:
        return CompetitionAnswer(
            why_them=(
                "Votre annonce est au niveau des concurrentes sur le prix, la garantie, "
                "les photos et les accessoires."
            ),
            actions=[
                {"kind": "description", "text": "Soignez la description pour vous démarquer."}
            ],
        )
    return CompetitionAnswer(
        why_them="Un acheteur pourrait les préférer car " + " ; ".join(reasons) + ".",
        actions=actions[:4],
    )


def analyse(shop, listing: Listing) -> dict:
    rivals_listings = closest(listing)
    mine = facts(listing)
    rivals = [facts(r) for r in rivals_listings]
    if not rivals:
        return {
            "listing_id": listing.pk,
            "competitors": [],
            "why_them": "",
            "actions": [],
            "used_ai": False,
            "note": "Aucune annonce concurrente assez proche pour le moment.",
        }
    data = {"mon_annonce": mine, "concurrentes": rivals}
    value, used_ai = llm.write(
        "insights_competition",
        "insights_competition",
        data,
        CompetitionAnswer,
        lambda: deterministic(mine, rivals),
        lambda v: [v.why_them, *(a.text for a in v.actions)],
        shop=shop,
    )
    return {
        "listing_id": listing.pk,
        "mine": mine,
        "competitors": [
            {**facts(r), "slug": r.slug, "city": r.city, "shop": r.shop.name if r.shop else None}
            for r in rivals_listings
        ],
        "why_them": value.why_them,
        "actions": [a.model_dump() for a in value.actions],
        "used_ai": used_ai,
    }
