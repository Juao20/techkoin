import re

PHONE_RE = re.compile(r"^\+22901\d{8}$")


def normalize_phone(raw: str) -> str | None:
    """Return a Beninese number in E.164 (+22901XXXXXXXX), or None if invalid.

    Accepts "+229 01 XX XX XX XX", "229...", the 10-digit local form "01XXXXXXXX"
    and the legacy 8-digit form (the "01" prefix is added).
    """
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("00229"):
        digits = digits[2:]
    if len(digits) == 8:
        digits = "229" + "01" + digits
    elif len(digits) == 10 and digits.startswith("01"):
        digits = "229" + digits
    candidate = "+" + digits
    return candidate if PHONE_RE.match(candidate) else None
