from typing import Any

from app.domain.models import PriorityResult, PriorityTier


def compute_priority(
    hotspot_count: int,
    max_frp: float,
    affected_area_km2: float,
    cluster_confidence: float,
    weather: dict[str, Any] | None = None,
) -> PriorityResult:
    """
    Stage 6: Explainable rule-based prioritization.
    Produces a heuristic score [0, 100] with explicit rule contributions.
    """
    rules: list[dict[str, Any]] = []
    score = 0.0

    # Rule 1: Hotspot density
    if hotspot_count >= 30:
        pts = 30.0
    elif hotspot_count >= 15:
        pts = 20.0
    else:
        pts = 10.0
    score += pts
    rules.append({"rule": "hotspot_count", "value": hotspot_count, "points": pts})

    # Rule 2: Peak Fire Radiative Power (MW)
    if max_frp >= 100.0:
        pts = 30.0
    elif max_frp >= 50.0:
        pts = 20.0
    elif max_frp >= 20.0:
        pts = 10.0
    else:
        pts = 5.0
    score += pts
    rules.append({"rule": "max_frp_mw", "value": round(max_frp, 2), "points": pts})

    # Rule 3: Cluster confidence
    pts = round(cluster_confidence * 20.0, 1)
    score += pts
    rules.append({"rule": "cluster_confidence", "value": round(cluster_confidence, 2), "points": pts})

    # Rule 4: Weather wind/humidity modifier (if available)
    wind = (weather or {}).get("wind_speed_kmh")
    humidity = (weather or {}).get("relative_humidity_pct")
    if wind is not None and wind >= 25.0:
        score += 12.0
        rules.append({"rule": "high_wind_kmh", "value": wind, "points": 12.0})
    if humidity is not None and humidity <= 30.0:
        score += 8.0
        rules.append({"rule": "low_humidity_pct", "value": humidity, "points": 8.0})

    score = min(100.0, round(score, 1))
    if score >= 80.0:
        tier = PriorityTier.CRITICAL
    elif score >= 60.0:
        tier = PriorityTier.HIGH
    elif score >= 35.0:
        tier = PriorityTier.MODERATE
    else:
        tier = PriorityTier.LOW

    return PriorityResult(score=score, tier=tier, rules_triggered=rules)
