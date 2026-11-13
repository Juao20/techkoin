"""Device model lookup shared by the autocomplete endpoint and the voice assistant."""

from .models import DeviceModel


def find_models(q: str, category: str | None = None, limit: int = 10) -> list[DeviceModel]:
    """Matches name, brand and aliases; every word of the query must be present."""
    qs = DeviceModel.objects.filter(is_active=True).select_related("brand")
    if category:
        qs = qs.filter(category=category)
    q = q.strip().lower()
    if not q:
        return list(qs[:limit])
    compact = q.replace(" ", "")
    matches = []
    for m in qs:
        haystack = f"{m.brand.name} {m.name}".lower()
        aliases = [a.lower() for a in m.aliases]
        if (
            all(part in haystack for part in q.split())
            or compact in haystack.replace(" ", "")
            or any(compact in a.replace(" ", "") for a in aliases)
        ):
            matches.append(m)
        if len(matches) == limit:
            break
    return matches
