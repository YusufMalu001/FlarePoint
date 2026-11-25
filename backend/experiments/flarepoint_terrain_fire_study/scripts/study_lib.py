import math
from typing import Sequence
import numpy as np
from scipy import stats


def classify_elevation(elev_m: float | None, edges: Sequence[float]) -> str | None:
    if elev_m is None or math.isnan(elev_m):
        return None
    for lo, hi in zip(edges, edges[1:]):
        if lo <= elev_m < hi:
            return f"{int(lo)}-{int(hi)}m" if hi < 5000 else f"{int(lo)}m+"
    return None


def classify_slope(slope_deg: float | None, edges: Sequence[float]) -> str | None:
    if slope_deg is None or math.isnan(slope_deg):
        return None
    for lo, hi in zip(edges, edges[1:]):
        if lo <= slope_deg < hi:
            return f"{int(lo)}-{int(hi)}deg" if hi < 90 else f"{int(lo)}deg+"
    return None


def classify_aspect_sector(
    aspect_deg: float | None, slope_deg: float | None, flat_threshold_deg: float = 5.0
) -> str:
    """Assign 8-sector compass class, excluding flat/near-flat terrain."""
    if slope_deg is None or math.isnan(slope_deg) or slope_deg < flat_threshold_deg:
        return "FLAT_UNDEFINED"
    if aspect_deg is None or math.isnan(aspect_deg):
        return "FLAT_UNDEFINED"
    sectors = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int(((aspect_deg + 22.5) % 360.0) // 45.0)
    return sectors[idx]


def benjamini_hochberg_fdr(p_values: Sequence[float]) -> list[float]:
    """Benjamini-Hochberg false discovery rate adjustment."""
    m = len(p_values)
    if m == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * m
    prev = 1.0
    for rank_rev, (orig_idx, p) in enumerate(reversed(indexed)):
        rank = m - rank_rev
        val = min(prev, (p * m) / rank)
        adjusted[orig_idx] = round(min(1.0, val), 6)
        prev = val
    return adjusted


def kruskal_by_group(values: Sequence[float], groups: Sequence[str]) -> dict:
    """Run Kruskal-Wallis H-test across groups with >= 2 observations each."""
    grouped: dict[str, list[float]] = {}
    for v, g in zip(values, groups):
        if v is not None and not math.isnan(v) and g is not None:
            grouped.setdefault(g, []).append(float(v))
    valid_groups = {k: v for k, v in grouped.items() if len(v) >= 2}
    if len(valid_groups) < 2:
        return {"test": "kruskal_wallis", "statistic": None, "p_value": None, "groups": len(valid_groups)}
    stat, pval = stats.kruskal(*valid_groups.values())
    n_total = sum(len(v) for v in valid_groups.values())
    # Epsilon-squared effect size for Kruskal-Wallis
    k = len(valid_groups)
    eps_sq = max(0.0, (float(stat) - k + 1) / max(1, n_total - k))
    return {
        "test": "kruskal_wallis",
        "statistic": round(float(stat), 4),
        "p_value": float(pval),
        "epsilon_squared": round(eps_sq, 4),
        "n_total": n_total,
        "groups": k,
    }
