"""IMEI and serial number checks (spec 8.2). Identifiers are never logged or returned."""

import re

from marketplace.crypto import identifier_hash

# Serial number patterns per brand (letters and digits, normalised to upper case).
SERIAL_PATTERNS = {
    "apple": r"[A-Z0-9]{10,12}",
    "samsung": r"[A-Z0-9]{11}",
    "hp": r"[A-Z0-9]{10}",
    "dell": r"[A-Z0-9]{7}",
    "lenovo": r"[A-Z0-9]{8,10}",
    "asus": r"[A-Z0-9]{12,15}",
    "acer": r"[A-Z0-9]{18,22}",
}
GENERIC_SERIAL = r"[A-Z0-9]{6,25}"


def normalize(value: str) -> str:
    return re.sub(r"[\s\-./]", "", value or "").upper()


def luhn_valid(digits: str) -> bool:
    if not digits.isdigit():
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def is_valid_imei(value: str) -> bool:
    n = normalize(value)
    return len(n) == 15 and luhn_valid(n)


def validate_identifier(value: str, category: str, brand_slug: str = "") -> str | None:
    """Return a French error message, or None when the identifier is acceptable."""
    n = normalize(value)
    if not n:
        return "Saisissez l'IMEI ou le numéro de série. Il ne sera jamais affiché."
    if n.isdigit() and len(n) == 15:
        if luhn_valid(n):
            return None
        return "Cet IMEI est invalide. Recomposez *#06# et recopiez les 15 chiffres."
    if category == "smartphone":
        return "L'IMEI d'un smartphone comporte 15 chiffres. Composez *#06# pour l'afficher."
    pattern = SERIAL_PATTERNS.get(brand_slug, GENERIC_SERIAL)
    if re.fullmatch(pattern, n):
        return None
    return "Ce numéro de série ne ressemble pas à celui de la marque. Vérifiez-le sur l'appareil."


def hash_identifier(value: str) -> str:
    return identifier_hash(normalize(value)) if value else ""
