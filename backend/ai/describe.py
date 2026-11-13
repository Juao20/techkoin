"""F2: assisted listing text. The model may only use the facts it is given."""

from __future__ import annotations

import re

from marketplace.models import Listing
from marketplace.services import format_storage, model_label

from . import client
from .schemas import ListingText

CONDITION = {
    "new_sealed": "neuf, sous emballage",
    "new_open": "neuf, boîte ouverte",
    "refurbished": "reconditionné",
    "used": "d'occasion",
}
GRADE = {"A": "comme neuf", "B": "bon état", "C": "traces visibles d'usage"}
ACCESSORY = {
    "charger": "chargeur",
    "box": "boîte d'origine",
    "cable": "câble",
    "case": "coque",
    "earphones": "écouteurs",
    "invoice": "facture",
}


def facts(listing: Listing) -> dict:
    """Listing data only: no seller, no contact, no IMEI."""
    f: dict = {
        "modele": model_label(listing),
        "categorie": listing.get_category_display() if listing.category else "",
        "etat": CONDITION.get(listing.condition_type, ""),
        "note_etat": GRADE.get(listing.grade, "") if listing.grade else "",
        "memoire_vive_go": listing.ram_gb,
        "stockage": format_storage(listing.storage_gb, listing.storage_type) or None,
        "processeur": listing.processor.name if listing.processor else None,
        "carte_graphique": listing.gpu.name if listing.gpu else None,
        "ecran_pouces": float(listing.screen_size_in) if listing.screen_size_in else None,
        "couleur": listing.color or None,
        "sante_batterie_pourcent": listing.battery_health_pct,
        "accessoires": [ACCESSORY[a] for a in listing.accessories if a in ACCESSORY],
        "garantie_mois": listing.warranty_months or None,
        "aucune_piece_remplacee": listing.replaced_parts == ["none"],
        "pieces_remplacees": [p for p in listing.replaced_parts if p != "none"],
        "5g": True if listing.network_5g else None,
        "double_sim": True if listing.dual_sim else None,
        "debloque_tout_operateur": (
            True
            if listing.carrier_unlocked and listing.category in ("smartphone", "tablet")
            else None
        ),
        "ville": listing.city or None,
        "negociable": listing.negotiable,
    }
    return {k: v for k, v in f.items() if v not in (None, "", [], False) or k == "negociable"}


def _numbers(value) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", str(value)))


def allowed_numbers(f: dict) -> set[str]:
    out: set[str] = set()
    for key, v in f.items():
        out |= _numbers(v) | _numbers(key)  # "5g" is a fact whose name carries the number
    return {n.replace(",", ".") for n in out}


def fallback_text(listing: Listing, f: dict) -> ListingText:
    """Template text: it states what the seller entered and nothing else."""
    model = f["modele"]
    storage = f.get("stockage")
    title = f"{model} {storage}".strip() if storage else model
    if f.get("note_etat"):
        title = f"{title}, {f['note_etat']}"
    title = title[:70].rstrip(" ,")

    sentences = [f"{model.capitalize() if model.islower() else model} {f['etat']}."]
    if f.get("note_etat"):
        sentences.append(f"État général : {f['note_etat']}.")
    specs = []
    if f.get("memoire_vive_go"):
        specs.append(f"{f['memoire_vive_go']} Go de mémoire vive")
    if storage:
        specs.append(f"{storage} de stockage")
    if f.get("processeur"):
        specs.append(f"processeur {f['processeur']}")
    if f.get("carte_graphique"):
        specs.append(f"carte graphique {f['carte_graphique']}")
    if f.get("ecran_pouces"):
        specs.append(f"écran de {f['ecran_pouces']} pouces")
    if specs:
        sentences.append("Caractéristiques : " + ", ".join(specs) + ".")
    if f.get("sante_batterie_pourcent"):
        sentences.append(f"Santé de la batterie : {f['sante_batterie_pourcent']} %.")
    if f.get("aucune_piece_remplacee"):
        sentences.append("Aucune pièce remplacée.")
    elif f.get("pieces_remplacees"):
        sentences.append("Pièces remplacées : " + ", ".join(f["pieces_remplacees"]) + ".")
    if f.get("accessoires"):
        sentences.append("Fourni avec : " + ", ".join(f["accessoires"]) + ".")
    if f.get("garantie_mois"):
        sentences.append(f"Garantie : {f['garantie_mois']} mois.")
    if f.get("ville"):
        sentences.append(f"Remise possible à {f['ville']}.")
    if listing.grade == "C":
        sentences.append(
            "Les traces d'usage sont visibles sur les photos : consultez-les avant d'acheter."
        )

    highlights = []
    if f.get("note_etat"):
        highlights.append(f"État : {f['note_etat']}")
    if specs:
        highlights.append(specs[0][0].upper() + specs[0][1:])
    if f.get("sante_batterie_pourcent"):
        highlights.append(f"Batterie à {f['sante_batterie_pourcent']} %")
    if f.get("accessoires"):
        highlights.append("Avec " + ", ".join(f["accessoires"][:2]))
    if f.get("garantie_mois"):
        highlights.append(f"Garantie {f['garantie_mois']} mois")
    for filler in (
        "Photos détaillées dans l'annonce",
        "Remise en main propre",
        f"Modèle : {model}",
    ):
        if len(highlights) >= 3:
            break
        highlights.append(filler)
    return ListingText(
        title=title or model[:70], description=" ".join(sentences), highlights=highlights[:3]
    )


FORBIDDEN_CLAIMS = ("jamais réparé", "jamais repare", "garanti à vie", "100 % fiable")


def run(listing: Listing, user=None) -> dict:
    f = facts(listing)
    allowed = allowed_numbers(f)

    def validate(text: ListingText) -> None:
        words = len(text.description.split())
        if not 80 <= words <= 150:
            raise ValueError(f"description de {words} mots")
        body = " ".join([text.title, text.description, *text.highlights]).lower()
        if any(c in body for c in FORBIDDEN_CLAIMS) and not f.get("aucune_piece_remplacee"):
            raise ValueError("promesse non vérifiable")
        invented = {n.replace(",", ".") for n in _numbers(body)} - allowed
        if invented:
            raise ValueError(f"chiffres inventés : {sorted(invented)}")

    result = client.complete(
        "describe",
        "describe",
        {"facts": f},
        ListingText,
        "smart",
        fallback=lambda: fallback_text(listing, f),
        user=user,
        validate=validate,
    )
    text = result.value
    return {
        "title": text.title,
        "description": text.description,
        "highlights": text.highlights,
        "used_ai": not result.fallback_used,
    }
