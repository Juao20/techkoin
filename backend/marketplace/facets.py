"""Facet counters (spec 6.4): how many results each filter option would give.

For every group the counts ignore that group's own filter, so the user sees what choosing another
option would return, the way shops and marketplaces usually show them. Same filters, same
functions as the search: nothing here knows how a filter works.
"""

from django.db.models import Count

from .models import Listing
from .search import apply_city, apply_filters

LIVE = [Listing.Status.ACTIVE, Listing.Status.RESERVED]
GROUPS = {
    "category": "category",
    "brand": "brand__slug",
    "condition": "condition_type",
    "grade": "grade",
}
FLAGS = (
    "gpu_dedicated",
    "5g",
    "dual_sim",
    "unlocked",
    "no_replaced_parts",
    "cellular",
    "stylus",
    "verified",
    "invoice",
    "secure_payment",
    "warranty",
)


def _without(params, *keys) -> dict:
    return {k: v for k, v in params.items() if k not in keys and k != "page"}


def _base(params, *exclude):
    qs = Listing.objects.filter(status__in=LIVE)
    scoped = _without(params, *exclude)
    qs = apply_filters(qs, scoped)
    if "city" not in exclude and params.get("city"):
        qs = apply_city(qs, params["city"])
    return qs


def _count(qs, field) -> dict[str, int]:
    rows = qs.exclude(**{field: ""}).values(field).annotate(n=Count("id")).order_by()
    return {str(r[field]): r["n"] for r in rows if r[field] is not None}


def facets(params) -> dict:
    out: dict = {name: _count(_base(params, name), field) for name, field in GROUPS.items()}
    shops = _base(params, "seller_type").filter(shop__isnull=False).count()
    everyone = _base(params, "seller_type").count()
    out["seller_type"] = {"shop": shops, "individual": everyone - shops}
    out["flags"] = {flag: apply_filters(_base(params, flag), {flag: "1"}).count() for flag in FLAGS}
    out["total"] = _base(params).count()
    return out
