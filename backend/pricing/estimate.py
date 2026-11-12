"""Price estimation (spec 7.1) and price badge (spec 7.2).

The estimate is computed here and nowhere else: a language model never produces a price.
The public interface is `estimate(...)`; a regression model could replace the body later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from catalog.models import DeviceModel


@dataclass(frozen=True)
class Estimate:
    low: int
    mid: int
    high: int
    sample_size: int
    indicative: bool


def round_price(value: float) -> int:
    step = settings.PRICING_ROUND_TO
    return int(round(value / step) * step)


def condition_coeff(condition_type: str, grade: str) -> float:
    coeffs = settings.PRICING_COEFFS["condition"]
    if condition_type in ("new_sealed", "new_open", "refurbished"):
        return coeffs[condition_type]
    return coeffs.get(grade or "B", coeffs["B"])


def extras_coeff(battery_health_pct: int | None, replaced_parts: list[str] | None) -> float:
    coeff = 1.0
    if battery_health_pct is not None and battery_health_pct < 80:
        coeff *= settings.PRICING_COEFFS["battery_below_80"]
    if replaced_parts and any(p != "none" for p in replaced_parts):
        coeff *= settings.PRICING_COEFFS["replaced_parts"]
    return coeff


def total_coeff(condition_type, grade, battery_health_pct, replaced_parts) -> float:
    return condition_coeff(condition_type, grade) * extras_coeff(battery_health_pct, replaced_parts)


def _quartiles(values: list[float]) -> tuple[float, float]:
    ordered = sorted(values)
    return _percentile(ordered, 0.25), _percentile(ordered, 0.75)


def _percentile(ordered: list[float], q: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _weighted_percentile(pairs: list[tuple[float, float]], q: float) -> float:
    """Weighted percentile with linear interpolation between cumulative weight midpoints."""
    pairs = sorted(pairs)
    total = sum(w for _, w in pairs)
    target = q * total
    cumulative = 0.0
    previous_value = pairs[0][0]
    previous_mid = 0.0
    for value, weight in pairs:
        mid = cumulative + weight / 2
        if target <= mid:
            if mid == previous_mid:
                return value
            ratio = (target - previous_mid) / (mid - previous_mid)
            return previous_value + (value - previous_value) * max(0.0, min(1.0, ratio))
        cumulative += weight
        previous_value, previous_mid = value, mid
    return pairs[-1][0]


def comparables(device_model: DeviceModel, storage_gb: int | None, exclude_pk=None):
    """Active listings and recent sales of the same model and storage."""
    from marketplace.models import Listing

    since = timezone.now() - timedelta(days=settings.PRICING_SOLD_WINDOW_DAYS)
    qs = Listing.objects.filter(device_model=device_model, price_fcfa__gt=0).filter(
        Q(status=Listing.Status.ACTIVE) | Q(status=Listing.Status.SOLD, sold_at__gte=since)
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    if storage_gb:
        exact = qs.filter(storage_gb=storage_gb)
        if exact.count() >= settings.PRICING_MIN_COMPARABLES or device_model.category not in (
            "laptop",
            "desktop",
        ):
            return exact
        # PCs: allow one storage tier up or down when there are too few exact matches.
        return qs.filter(storage_gb__gte=storage_gb // 2, storage_gb__lte=storage_gb * 2)
    return qs


def _indicative(device_model: DeviceModel, coeff: float) -> Estimate | None:
    ref = device_model.reference_price_new_fcfa
    if not ref:
        return None
    age = max(0, timezone.now().year - (device_model.release_year or timezone.now().year))
    # -18 % the first year, -12 % per further year, never below 20 % of the new price.
    depreciation = 1.0 if age == 0 else max(0.20, 0.82 - 0.12 * (age - 1))
    mid = ref * depreciation * coeff
    mid = min(mid, ref)  # a device is never estimated above its new price
    return Estimate(
        low=round_price(mid * 0.85),
        mid=round_price(mid),
        high=round_price(mid * 1.15),
        sample_size=0,
        indicative=True,
    )


def estimate(
    device_model: DeviceModel | None,
    storage_gb: int | None = None,
    ram_gb: int | None = None,  # kept in the interface for a future regression model
    condition_type: str = "used",
    grade: str = "",
    battery_health_pct: int | None = None,
    replaced_parts: list[str] | None = None,
    city: str = "",  # idem
    exclude_pk=None,
) -> Estimate | None:
    if device_model is None:
        return None
    own = total_coeff(condition_type, grade, battery_health_pct, replaced_parts)

    from marketplace.models import Listing

    pairs: list[tuple[float, float]] = []
    for c in comparables(device_model, storage_gb, exclude_pk):
        normalized = c.price_fcfa / total_coeff(
            c.condition_type, c.grade, c.battery_health_pct, c.replaced_parts
        )
        weight = settings.PRICING_SOLD_WEIGHT if c.status == Listing.Status.SOLD else 1.0
        pairs.append((normalized, weight))

    if len(pairs) < settings.PRICING_MIN_COMPARABLES:
        return _indicative(device_model, own)

    q1, q3 = _quartiles([v for v, _ in pairs])
    iqr = q3 - q1
    kept = [(v, w) for v, w in pairs if q1 - 1.5 * iqr <= v <= q3 + 1.5 * iqr]
    if len(kept) < settings.PRICING_MIN_COMPARABLES:
        kept = pairs
    low = _weighted_percentile(kept, 0.25) * own
    mid = _weighted_percentile(kept, 0.50) * own
    high = _weighted_percentile(kept, 0.75) * own
    return Estimate(
        low=round_price(low),
        mid=round_price(mid),
        high=round_price(high),
        sample_size=len(kept),
        indicative=False,
    )


def price_badge(price_fcfa: int, est: Estimate | None) -> str:
    """'good_deal', 'fair', 'above_market' or 'unknown' (no badge)."""
    if est is None or est.indicative or est.mid <= 0 or price_fcfa <= 0:
        return "unknown"
    ratio = price_fcfa / est.mid
    if ratio <= 0.90:
        return "good_deal"
    if ratio >= 1.15:
        return "above_market"
    if ratio <= 1.10:
        return "fair"
    return "unknown"  # between 1.10 and 1.15: no badge


def estimate_listing(listing) -> Estimate | None:
    return estimate(
        listing.device_model,
        storage_gb=listing.storage_gb,
        ram_gb=listing.ram_gb,
        condition_type=listing.condition_type,
        grade=listing.grade,
        battery_health_pct=listing.battery_health_pct,
        replaced_parts=listing.replaced_parts,
        city=listing.city,
        exclude_pk=listing.pk,
    )
