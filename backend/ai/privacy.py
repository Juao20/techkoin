"""Nothing personal goes to the language model.

Prompts are built from listing data and aggregates only. This module is a second line of
defence: every outgoing request is scanned, and one that looks personal is never sent (the
feature answers with its fallback instead).
"""

import re

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Benin numbers (+229 01 97 00 00 00, 97000000...) and any long digit run such as an IMEI.
PHONE_RE = re.compile(
    r"(?<![\d.])(?:\+?229[\s.-]?)?(?:01[\s.-]?)?[2-9]\d[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}(?![\d])"
)
IMEI_RE = re.compile(r"(?<!\d)\d{15}(?!\d)")
FORBIDDEN_KEYS = {
    "imei",
    "imei_or_serial",
    "imei_hash",
    "phone",
    "whatsapp_number",
    "email",
    "password",
    "first_name",
    "last_name",
    "seller_name",
    "identity_document",
    "identity_selfie",
    "document",
}


class PersonalDataError(ValueError):
    pass


def _walk(value, path=""):
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise PersonalDataError(f"clé interdite : {key}")
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item, path)
    elif isinstance(value, str):
        yield value


def check(payload) -> None:
    """Raise PersonalDataError if the payload contains a personal identifier."""
    for text in _walk(payload):
        if EMAIL_RE.search(text) or IMEI_RE.search(text) or PHONE_RE.search(text):
            raise PersonalDataError("donnée personnelle détectée")


def scrub_text(text: str) -> str:
    """Remove contact details from free text (a description a seller wrote, a user question)."""
    text = EMAIL_RE.sub("[contact retiré]", text)
    text = PHONE_RE.sub("[contact retiré]", text)
    return IMEI_RE.sub("[numéro retiré]", text)
