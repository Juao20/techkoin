"""All listing search and filtering goes through this module.

Keeping text search in one place lets us swap in PostgreSQL full-text search later
without touching views or serializers (see TECHKOIN_SPEC.md, section 3.1).
"""

from django.db.models import (
    Case,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    Q,
    QuerySet,
    Value,
    When,
)
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast

from catalog.models import City, Processor

from .models import Listing

PAGE_SIZE = 24
SORTS = {"relevance", "price_asc", "price_desc", "recent", "best_deal"}


def csv(params, key: str) -> list[str]:
    raw = params.get(key, "")
    return [v.strip() for v in raw.split(",") if v.strip()]


def to_int(params, key: str) -> int | None:
    try:
        return int(params.get(key, ""))
    except (TypeError, ValueError):
        return None


def flag(params, key: str) -> bool:
    return params.get(key, "") in {"1", "true", "yes"}


def text_search(qs: QuerySet, text: str) -> QuerySet:
    """Every word must appear in the searchable text (title, model, aliases, category)."""
    for word in text.lower().split():
        qs = qs.filter(search_text__contains=word)
    return qs


def nearby_city_names(slug: str) -> tuple[str, list[str]] | None:
    city = City.objects.filter(slug=slug).first()
    if not city:
        return None
    return city.name, list(city.nearby.values_list("name", flat=True))


def apply_filters(qs: QuerySet, params) -> QuerySet:
    q = params.get("q", "").strip()
    if q:
        qs = text_search(qs, q)

    if cat := params.get("category"):
        qs = qs.filter(category=cat)
    if brands := csv(params, "brand"):
        qs = qs.filter(brand__slug__in=brands)
    if (v := to_int(params, "price_min")) is not None:
        qs = qs.filter(price_fcfa__gte=v)
    if (v := to_int(params, "price_max")) is not None:
        qs = qs.filter(price_fcfa__lte=v)
    if conds := csv(params, "condition"):
        qs = qs.filter(condition_type__in=conds)
    if grades := csv(params, "grade"):
        qs = qs.filter(grade__in=[g.upper() for g in grades])

    if (v := to_int(params, "ram_min")) is not None:
        qs = qs.filter(ram_gb__gte=v)
    if (v := to_int(params, "storage_min")) is not None:
        qs = qs.filter(storage_gb__gte=v)
    if st := csv(params, "storage_type"):
        qs = qs.filter(storage_type__in=st)
    if flag(params, "gpu_dedicated"):
        qs = qs.filter(gpu_dedicated=True)
    if kb := csv(params, "keyboard"):
        qs = qs.filter(keyboard_layout__in=kb)
    if osv := csv(params, "os"):
        qs = qs.filter(os__in=osv)
    if (v := to_int(params, "screen_min")) is not None:
        qs = qs.filter(screen_size_in__gte=v)
    if (v := to_int(params, "screen_max")) is not None:
        qs = qs.filter(screen_size_in__lte=v)
    if fams := csv(params, "cpu_family"):
        qs = qs.filter(processor__family__in=fams)
    if (gen := to_int(params, "cpu_gen_min")) is not None:
        ids = [
            p.id
            for p in Processor.objects.filter(vendor="Intel")
            if p.generation.isdigit() and int(p.generation) >= gen
        ]
        qs = qs.filter(processor_id__in=ids)

    if (v := to_int(params, "battery_min")) is not None:
        qs = qs.filter(battery_health_pct__gte=v)
    if flag(params, "5g"):
        qs = qs.filter(network_5g=True)
    if flag(params, "dual_sim"):
        qs = qs.filter(dual_sim=True)
    if flag(params, "unlocked"):
        qs = qs.filter(carrier_unlocked=True)
    if flag(params, "no_replaced_parts"):
        qs = qs.filter(Q(replaced_parts=[]) | Q(replaced_parts=["none"]))
    if flag(params, "cellular"):
        qs = qs.filter(cellular=True)
    if flag(params, "stylus"):
        qs = qs.filter(stylus_included=True)

    if flag(params, "verified"):
        qs = qs.filter(
            Q(shop__verification_status="verified") | Q(seller__identity_status="verified")
        )
    seller_type = params.get("seller_type")
    if seller_type == "shop":
        qs = qs.filter(shop__isnull=False)
    elif seller_type == "individual":
        qs = qs.filter(shop__isnull=True)
    if flag(params, "warranty"):
        qs = qs.filter(warranty_months__gt=0)
    elif (v := to_int(params, "warranty")) is not None:
        qs = qs.filter(warranty_months__gte=v)
    if flag(params, "invoice"):
        qs = qs.filter(has_invoice=True)
    if usage := params.get("usage"):
        # Advised usage: a score of 7 or more by default (see pricing/usage.py); the smart
        # search may lower the bar with `usage_min` when nothing reaches 7.
        floor = to_int(params, "usage_min")
        qs = qs.filter(**{f"usage_scores__{usage}__gte": floor if floor else 7})
    if flag(params, "secure_payment"):
        qs = qs.filter(accepts_secure_payment=True)
    return qs


def apply_city(qs: QuerySet, slug: str) -> QuerySet:
    """Chosen city first, then nearby cities (static proximity table), others excluded."""
    found = nearby_city_names(slug)
    if not found:
        return qs
    name, nearby = found
    return qs.filter(city__in=[name, *nearby]).annotate(
        city_rank=Case(
            When(city=name, then=Value(0)), default=Value(1), output_field=IntegerField()
        )
    )


USAGES = {
    "office", "study", "dev", "gaming", "creative", "battery", "everyday", "photo", "business",
}  # fmt: skip


def usage_sort_key(sort: str) -> str | None:
    """`usage:gaming` ranks listings by their usage score, best first."""
    if sort.startswith("usage:") and sort[6:] in USAGES:
        return sort[6:]
    return None


def apply_sort(qs: QuerySet, sort: str, has_city: bool) -> QuerySet:
    prefix = ["city_rank"] if has_city else []
    if key := usage_sort_key(sort):

        score = Cast(KeyTextTransform(key, "usage_scores"), FloatField())
        return qs.annotate(usage_rank=score).order_by(
            *prefix, F("usage_rank").desc(nulls_last=True), "price_fcfa"
        )
    if sort == "price_asc":
        return qs.order_by(*prefix, "price_fcfa", "-published_at")
    if sort == "price_desc":
        return qs.order_by(*prefix, "-price_fcfa", "-published_at")
    if sort == "recent":
        return qs.order_by(*prefix, "-published_at")
    if sort == "best_deal":

        return (
            qs.filter(estimate_mid__gt=0)
            .exclude(price_badge="unknown")
            .annotate(
                deal_ratio=ExpressionWrapper(
                    F("price_fcfa") * 1.0 / F("estimate_mid"), output_field=FloatField()
                )
            )
            .order_by(*prefix, "deal_ratio")
        )
    # relevance: verified seller bonus, complete photos bonus, then freshness
    verified = Q(shop__verification_status="verified") | Q(seller__identity_status="verified")
    return (
        qs.annotate(photo_count=Count("photos", distinct=True))
        .annotate(
            relevance=Case(
                When(verified, then=Value(2)), default=Value(0), output_field=IntegerField()
            )
            + Case(
                When(photo_count__gte=6, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by(*prefix, "-relevance", "-published_at")
    )


def search_listings(params) -> QuerySet:
    qs = Listing.objects.filter(
        status__in=[Listing.Status.ACTIVE, Listing.Status.RESERVED]
    ).select_related("brand", "device_model", "processor", "shop", "seller")
    qs = apply_filters(qs, params)
    city = params.get("city")
    has_city = False
    if city:
        before = qs
        qs = apply_city(qs, city)
        has_city = qs is not before
    requested = params.get("sort", "")
    sort = requested if requested in SORTS or usage_sort_key(requested) else "relevance"
    return apply_sort(qs, sort, has_city).prefetch_related("photos")
