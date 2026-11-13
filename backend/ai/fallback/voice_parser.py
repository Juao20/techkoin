"""Rule based extraction from a dictated sentence (F3 fallback, used when the model is down)."""

from __future__ import annotations

import re

from ..schemas import VoiceFields
from .query_parser import plain

ACCESSORY_WORDS = {
    "charger": ("chargeur",),
    "box": ("boite",),
    "cable": ("cable",),
    "case": ("coque",),
    "earphones": ("ecouteur", "ecouteurs", "airpods"),
    "invoice": ("facture",),
}
COLORS = {
    "noir": "Noir",
    "blanc": "Blanc",
    "bleu": "Bleu",
    "rouge": "Rouge",
    "vert": "Vert",
    "gris": "Gris",
    "argent": "Argent",
    "or": "Or",
    "rose": "Rose",
    "violet": "Violet",
}
DEFECT_WORDS = ("rayure", "fissure", "casse", "choc", "bosse", "raye", "fele", "defaut", "panne")


def parse(text: str, known_terms=lambda token: False) -> VoiceFields:
    t = plain(text)
    out = VoiceFields()

    if m := re.search(r"(\d+)\s*(?:giga|go|gb)(?:\s+de\s+ram)\b", t):
        out.ram_gb = int(m.group(1))
    for m in re.finditer(r"(\d+)\s*(giga|gigas|go|gb|to|tb)\b", t):
        value = int(m.group(1)) * (1024 if m.group(2) in ("to", "tb") else 1)
        if out.ram_gb == value and re.search(r"ram", t[m.start() : m.end() + 8]):
            continue
        if value >= 64:
            out.storage_gb = value
        elif out.ram_gb is None and value <= 32:
            out.ram_gb = value
    if m := re.search(r"batterie\s*(?:a|de|est a|:)?\s*(\d{2,3})", t) or re.search(
        r"(\d{2,3})\s*%?\s*(?:de\s+)?(?:batterie|sante)", t
    ):
        value = int(m.group(1))
        if 1 <= value <= 100:
            out.battery_health_pct = value

    for key, words in ACCESSORY_WORDS.items():
        if any(re.search(rf"\b{w}\b", t) for w in words):
            out.accessories.append(key)
    for word, label in COLORS.items():
        if re.search(rf"\b{word}\b", t):
            out.color = label
            break

    defect = next((w for w in DEFECT_WORDS if w in t), None)
    if re.search(r"neuf (?:scelle|sous emballage)|jamais ouvert", t):
        out.condition_type = "new_sealed"
    elif re.search(r"\bneuf\b", t) and "comme neuf" not in t:
        out.condition_type = "new_open"
    elif re.search(r"reconditionn", t):
        out.condition_type = "refurbished"
    elif "occasion" in t or defect or out.battery_health_pct:
        out.condition_type = "used"
    if out.condition_type in ("used", "refurbished", None):
        if defect and re.search(r"fissur|casse|panne|fele", t):
            out.grade = "C"
        elif defect:
            out.grade = "B"
        elif "comme neuf" in t or "parfait" in t:
            out.grade = "A"
    if defect:
        m = re.search(rf"([^,.;]*{defect}[^,.;]*)", text, re.I)
        out.defects = m.group(1).strip() if m else None

    if re.search(r"\b(iphone|galaxy|redmi|tecno|infinix|itel|pixel|oppo|huawei)\b", t):
        out.category = "smartphone"
    elif re.search(r"\b(ipad|tablette|tab)\b", t):
        out.category = "tablet"
    elif re.search(r"\b(macbook|thinkpad|laptop|pc|ordi|ordinateur)\b", t):
        out.category = "laptop"

    # The model is the first group of words that names a device ("iPhone 12", "Galaxy A54").
    words = re.findall(r"[a-z0-9]+", t)
    for i, word in enumerate(words):
        if known_terms(word):
            span = [word]
            for nxt in words[i + 1 : i + 3]:
                if nxt.isdigit() and len(nxt) <= 3 and len(span) == 1 or known_terms(nxt):
                    span.append(nxt)
                else:
                    break
            out.model_text = " ".join(span)
            break
    return out
