"""Rule based answers for the buyer assistant (F4 fallback): they read the listing's data."""

from __future__ import annotations

import re

from ..schemas import AssistantAnswer
from .query_parser import plain

USAGE_LABEL = {
    "office": "la bureautique",
    "study": "les études",
    "dev": "le développement",
    "gaming": "les jeux",
    "creative": "la photo et la vidéo",
    "battery": "l'autonomie",
    "everyday": "un usage quotidien",
    "photo": "la photo",
    "business": "un usage professionnel",
}
PC_ONLY = {"creative", "dev", "office", "study"}
USAGE_QUESTION = [
    ("creative", r"premiere|montage|photoshop|video|illustrator|davinci|after effects|graphisme"),
    ("gaming", r"jeu|jeux|jouer|gaming|fortnite|fifa|gta|call of duty|valorant"),
    ("dev", r"cod|programm|develop|android studio|visual studio"),
    ("office", r"bureautique|word|excel|powerpoint|bureau|travail"),
    ("study", r"etude|ecole|cours|universite|etudiant"),
    ("photo", r"photo|appareil photo|camera"),
    ("everyday", r"quotidien|tous les jours|usage courant"),
    ("business", r"professionnel|business"),
]


def _verdict(score: float) -> str:
    if score >= 7:
        return "convient bien"
    if score >= 5:
        return "convient pour un usage léger à moyen"
    return "sera limité"


def _missing(question: str) -> AssistantAnswer:
    return AssistantAnswer(
        answer="Cette information n'est pas indiquée dans l'annonce. "
        "Vous pouvez poser la question au vendeur.",
        information_missing=True,
        suggested_seller_question=question,
    )


def answer(question: str, ctx: dict) -> AssistantAnswer:
    q = plain(question)
    f = ctx["facts"]
    scores = ctx.get("usage_scores", {})

    for usage, pattern in USAGE_QUESTION:
        if not re.search(pattern, q):
            continue
        if scores and usage not in scores and usage in PC_ONLY:
            # A phone or tablet has no score for computer tasks: say so, with the scores it has.
            known = ", ".join(
                f"{USAGE_LABEL[k]} {v:g}/10" for k, v in scores.items() if k != "battery"
            )
            return AssistantAnswer(
                answer="Cette utilisation est limitée sur un smartphone ou une tablette. "
                f"Scores de cet appareil : {known}."
            )
        if usage in scores:
            score = scores[usage]
            text = (
                f"Pour {USAGE_LABEL[usage]}, cet appareil obtient {score:g}/10 : "
                f"il {_verdict(score)}."
            )
            if usage in ("creative", "gaming", "dev") and score < 7:
                text += " Pour un usage intensif, comparez avec un modèle mieux noté."
            return AssistantAnswer(answer=text)

    if re.search(r"batterie|autonomie|cycle", q):
        parts = []
        if f.get("sante_batterie_pourcent"):
            parts.append(
                f"La santé de la batterie déclarée est de {f['sante_batterie_pourcent']} %."
            )
        if ctx.get("battery_autonomy_h"):
            parts.append(f"Autonomie annoncée : {ctx['battery_autonomy_h']} h.")
        if ctx.get("battery_cycles"):
            parts.append(f"Nombre de cycles : {ctx['battery_cycles']}.")
        if parts and scores.get("battery") is not None:  # a score built on real data only
            parts.append(f"Score d'autonomie : {scores['battery']:g}/10.")
        return AssistantAnswer(answer=" ".join(parts)) if parts else _missing(question)
    if re.search(r"garantie", q):
        months = f.get("garantie_mois")
        text = (
            f"Le vendeur offre {months} mois de garantie."
            if months
            else "Aucune garantie n'est indiquée."
        )
        return AssistantAnswer(answer=text)
    if re.search(r"facture|recu", q):
        return AssistantAnswer(
            answer=(
                "Une facture est fournie."
                if "facture" in f.get("accessoires", [])
                else "Aucune facture n'est indiquée dans l'annonce."
            ),
            information_missing="facture" not in f.get("accessoires", []),
            suggested_seller_question=None if "facture" in f.get("accessoires", []) else question,
        )
    if re.search(r"accessoire|chargeur|boite|cable|coque|ecouteur|fourni|livre|inclus", q):
        items = f.get("accessoires", [])
        return AssistantAnswer(
            answer=(
                ("Fourni avec : " + ", ".join(items) + ".")
                if items
                else "L'appareil est vendu seul."
            )
        )
    if re.search(r"piece|repar|remplac|ecran d origine|ouvert", q):
        if f.get("aucune_piece_remplacee"):
            return AssistantAnswer(answer="Le vendeur indique qu'aucune pièce n'a été remplacée.")
        if f.get("pieces_remplacees"):
            return AssistantAnswer(
                answer="Pièces remplacées déclarées : " + ", ".join(f["pieces_remplacees"]) + "."
            )
        return _missing(question)
    if re.search(r"etat|rayure|defaut|abime|fissur|casse|grade", q):
        grade = f.get("note_etat")
        if grade:
            return AssistantAnswer(
                answer=f"État déclaré : {grade} (note {ctx.get('grade') or '-'}). "
                "Les photos montrent les traces éventuelles."
            )
        return _missing(question)
    if re.search(r"icloud|google|compte|verrou|bloque", q):
        if ctx.get("account_removed"):
            return AssistantAnswer(
                answer="Le vendeur déclare avoir retiré son compte (iCloud ou Google) "
                "de l'appareil. Vérifiez-le à la remise."
            )
        return _missing(question)
    if re.search(r"\bram\b|memoire vive", q):
        return (
            AssistantAnswer(answer=f"Mémoire vive : {f['memoire_vive_go']} Go.")
            if f.get("memoire_vive_go")
            else _missing(question)
        )
    if re.search(r"stockage|disque|ssd|espace|capacite", q):
        return (
            AssistantAnswer(answer=f"Stockage : {f['stockage']}.")
            if f.get("stockage")
            else _missing(question)
        )
    if re.search(r"processeur|cpu|puce|chipset", q):
        return (
            AssistantAnswer(answer=f"Processeur : {f['processeur']}.")
            if f.get("processeur")
            else _missing(question)
        )
    if re.search(r"ecran|pouce|resolution", q):
        if f.get("ecran_pouces"):
            return AssistantAnswer(answer=f"Écran de {f['ecran_pouces']} pouces.")
        return _missing(question)
    if re.search(r"5g|double sim|dual sim|debloque|operateur", q):
        bits = []
        if f.get("5g"):
            bits.append("compatible 5G")
        if f.get("double_sim"):
            bits.append("double SIM")
        if f.get("debloque_tout_operateur"):
            bits.append("débloqué tout opérateur")
        return (
            AssistantAnswer(answer="Cet appareil est " + ", ".join(bits) + ".")
            if bits
            else _missing(question)
        )
    if re.search(r"prix|negoci|cher|affaire|valeur|estimation", q):
        est = ctx.get("estimate")
        if not est:
            return AssistantAnswer(
                answer="Aucune estimation de prix n'est disponible pour ce modèle."
            )
        text = (
            f"Prix du marché estimé entre {est['low']:,} et {est['high']:,} FCFA "
            f"(médiane {est['mid']:,} FCFA)."
        ).replace(",", " ")
        if est.get("indicative"):
            text += " Estimation indicative : peu d'annonces comparables."
        if f.get("negociable"):
            text += " Le vendeur indique que le prix est négociable."
        return AssistantAnswer(answer=text)
    return _missing(question)
