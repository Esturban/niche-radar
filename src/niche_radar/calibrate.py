from __future__ import annotations

from .utils import safe_mean


def normalize_trend_batch(
    series_by_term: dict[str, list[float]],
    anchor_terms: list[str],
) -> tuple[dict[str, dict], bool]:
    anchor_values = [safe_mean(series_by_term.get(anchor, [])) for anchor in anchor_terms]
    anchor_mean = safe_mean([value for value in anchor_values if value > 0])
    if anchor_mean <= 0:
        return {}, False

    normalized: dict[str, dict] = {}
    for term, series in series_by_term.items():
        if term in anchor_terms:
            continue
        if not series:
            normalized[term] = {"trend_strength_raw": 0.0, "trend_velocity_raw": 0.0}
            continue
        first_half = safe_mean(series[: max(1, len(series) // 2)])
        second_half = safe_mean(series[max(1, len(series) // 2) :])
        normalized[term] = {
            "trend_strength_raw": safe_mean(series) / anchor_mean,
            "trend_velocity_raw": (second_half - first_half) / anchor_mean,
        }
    return normalized, True

