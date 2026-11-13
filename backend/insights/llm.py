"""Shared plumbing for the Pro analyses: numbers come from Django, the model only words them.

`write()` asks the model for text, rejects an answer that contains a number it was not given,
and falls back to the deterministic text otherwise. Results are cached for a few hours per shop
and input, so reopening the dashboard does not call the model again.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from ai import cache, client
from ai.describe import _numbers

SMALL_NUMBERS = {str(n) for n in range(0, 6)}  # « 3 actions », « 2 photos »: harmless to allow
CACHE_TTL = timedelta(hours=6)


def allowed(data) -> set[str]:
    return {n.replace(",", ".") for n in _numbers(data)} | SMALL_NUMBERS


def invented_numbers(texts: list[str], data) -> set[str]:
    found = {n.replace(",", ".") for n in _numbers(" ".join(texts))}
    return found - allowed(data)


def write[T](
    feature: str,
    prompt: str,
    data,
    schema: type[T],
    fallback: Callable[[], T],
    texts: Callable[[T], list[str]],
    *,
    shop,
    extra_validate: Callable[[T], None] | None = None,
) -> tuple[T, bool]:
    """Return (value, used_ai). `texts(value)` lists the sentences to check for invented numbers."""
    key = cache.make_key(feature, {"shop": shop.pk, "data": data})
    if (hit := cache.get(key)) is not None:
        return schema.model_validate(hit["value"]), hit["used_ai"]

    def validate(value: T) -> None:
        bad = invented_numbers(texts(value), data)
        if bad:
            raise ValueError(f"chiffres inventés : {sorted(bad)}")
        if extra_validate:
            extra_validate(value)

    result = client.complete(
        feature,
        prompt,
        {"data": data},
        schema,
        "smart",
        fallback=fallback,
        user=shop.owner,
        shop=shop,
        validate=validate,
    )
    used_ai = not result.fallback_used
    if used_ai:  # a fallback is cheap and must not hide the model once it answers again
        cache.put(key, feature, {"value": result.value.model_dump(), "used_ai": True}, CACHE_TTL)
    return result.value, used_ai
