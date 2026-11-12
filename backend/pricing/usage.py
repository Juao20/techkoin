"""Usage scores from 0 to 10 (spec 7.3).

Every score is a weighted sum (weights add up to 1) of sub-scores that are each scaled to 0-10:

PC (laptop, desktop)
  office    0.35 CPU + 0.25 RAM + 0.25 storage + 0.15 screen
  study     0.30 CPU + 0.30 RAM + 0.20 storage + 0.20 battery
  dev       0.45 CPU + 0.30 RAM + 0.15 storage + 0.10 screen
  gaming    0.55 GPU + 0.25 CPU + 0.10 RAM + 0.10 refresh rate
  creative  0.30 CPU + 0.25 GPU + 0.25 RAM + 0.20 screen
  battery   autonomy in hours when known, otherwise estimated from cycles and the CPU

Phone, tablet
  everyday  0.50 chip + 0.30 RAM + 0.20 storage
  photo     0.35 chip + 0.35 storage + 0.30 screen
  gaming    0.55 chip + 0.25 RAM + 0.20 refresh rate
  battery   0.70 battery health + 0.30 efficiency (a faster chip draws more)
  business  0.30 chip + 0.30 RAM + 0.20 storage + 0.20 biometrics

Missing data counts as an average value (5), never as zero, so an incomplete listing is not
punished twice. The advised usage is the best score, provided it reaches 7.
"""

from __future__ import annotations

ADVISED_THRESHOLD = 7.0
PC_USAGES = ("office", "study", "dev", "gaming", "creative", "battery")
MOBILE_USAGES = ("everyday", "photo", "gaming", "battery", "business")
NEUTRAL = 5.0

RAM_POINTS = [(2, 1), (4, 3), (8, 5.5), (16, 8), (32, 10)]
AUTONOMY_POINTS = [(2, 1), (5, 4), (8, 6.5), (12, 8.5), (16, 10)]
PIXEL_POINTS = [(0.9e6, 3), (2.07e6, 6), (4.1e6, 8.5), (8.3e6, 10)]  # 720p-ish, FHD, QHD, 4K
REFRESH_POINTS = [(60, 4), (90, 7), (120, 9), (144, 10)]
STORAGE_KIND = {"ssd": 10, "ufs": 10, "hybrid": 5, "emmc": 4, "hdd": 2}


def scale(value: float | None, points: list[tuple[float, float]]) -> float:
    """Linear interpolation between (input, score) points; clamps outside the range."""
    if value is None:
        return NEUTRAL
    if value <= points[0][0]:
        return float(points[0][1])
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        if value <= x1:
            return y0 + (y1 - y0) * (value - x0) / (x1 - x0)
    return float(points[-1][1])


def _perf(component) -> float:
    return component.perf_score / 10 if component else NEUTRAL


def _pixels(resolution: str) -> float | None:
    try:
        w, h = resolution.lower().replace("×", "x").split("x")[:2]
        return float(w) * float(h)
    except (ValueError, AttributeError):
        return None


def _screen(listing) -> float:
    pixel_score = scale(_pixels(listing.screen_resolution), PIXEL_POINTS)
    return (pixel_score + scale(listing.refresh_rate_hz, REFRESH_POINTS)) / 2


def _storage(listing) -> float:
    kind = STORAGE_KIND.get(listing.storage_type, NEUTRAL)
    size = scale(listing.storage_gb, [(64, 3), (256, 6), (512, 8), (1024, 10)])
    return 0.6 * kind + 0.4 * size if listing.storage_type else size


def _pc_battery(listing) -> float:
    if listing.battery_autonomy_h:
        return scale(listing.battery_autonomy_h, AUTONOMY_POINTS)
    if listing.category == "desktop":
        return 0.0
    wear = scale(listing.battery_cycles, [(0, 9), (300, 7), (600, 5), (1000, 2)])
    return max(0.0, wear - 0.2 * max(0.0, _perf(listing.processor) - 5))


def _pc_scores(listing) -> dict[str, float]:
    cpu, ram = _perf(listing.processor), scale(listing.ram_gb, RAM_POINTS)
    gpu = _perf(listing.gpu) if listing.gpu_id else 2.0  # integrated graphics
    storage, screen, battery = _storage(listing), _screen(listing), _pc_battery(listing)
    refresh = scale(listing.refresh_rate_hz, REFRESH_POINTS)
    return {
        "office": 0.35 * cpu + 0.25 * ram + 0.25 * storage + 0.15 * screen,
        "study": 0.30 * cpu + 0.30 * ram + 0.20 * storage + 0.20 * battery,
        "dev": 0.45 * cpu + 0.30 * ram + 0.15 * storage + 0.10 * screen,
        "gaming": 0.55 * gpu + 0.25 * cpu + 0.10 * ram + 0.10 * refresh,
        "creative": 0.30 * cpu + 0.25 * gpu + 0.25 * ram + 0.20 * screen,
        "battery": battery,
    }


def _mobile_scores(listing) -> dict[str, float]:
    chip, ram = _perf(listing.processor), scale(listing.ram_gb, RAM_POINTS)
    storage, screen = _storage(listing), _screen(listing)
    refresh = scale(listing.refresh_rate_hz, REFRESH_POINTS)
    health = (
        listing.battery_health_pct / 10 if listing.battery_health_pct else 9.0
    )  # new devices have no wear
    return {
        "everyday": 0.50 * chip + 0.30 * ram + 0.20 * storage,
        "photo": 0.35 * chip + 0.35 * storage + 0.30 * screen,
        "gaming": 0.55 * chip + 0.25 * ram + 0.20 * refresh,
        "battery": 0.70 * health + 0.30 * (10 - 0.4 * chip),
        "business": 0.30 * chip
        + 0.30 * ram
        + 0.20 * storage
        + 0.20 * (10 if listing.biometrics_ok else 3),
    }


def usage_scores(listing) -> dict[str, float]:
    raw = (
        _pc_scores(listing)
        if listing.category in ("laptop", "desktop")
        else _mobile_scores(listing)
    )
    return {key: round(max(0.0, min(10.0, value)), 1) for key, value in raw.items()}


def advised_usage(scores: dict[str, float]) -> str | None:
    if not scores:
        return None
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] >= ADVISED_THRESHOLD else None
