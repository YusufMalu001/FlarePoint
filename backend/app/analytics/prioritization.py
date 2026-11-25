from typing import Any

from app.domain.models import PriorityResult, PriorityTier

DEFAULT_WEIGHTS = {
    "observation_frequency": 0.25,
    "radiative_power": 0.30,
    "confidence": 0.20,
    "weather_risk": 0.15,
    "persistence": 0.10,
}


def compute_priority(
    hotspot_count: int,
    max_frp: float,
    affected_area_km2: float,
    cluster_confidence: float,
    weather: dict[str, Any] | None = None,
    lifetime_hours: float = 1.0,
    weights: dict[str, float] | None = None,
) -> PriorityResult:
    """
    Phase G: Configurable, explainable rule-based prioritization.
    Accounts for observation frequency (hotspots/hour) rather than raw count alone,
    handles missing weather/FRP data explicitly, and is NOT a probability of danger.
    """
    w = weights or DEFAULT_WEIGHTS
    rules: list[dict[str, Any]] = []

    # 1. Observation frequency (detections per hour, capped at 100)
    freq = hotspot_count / max(1.0, lifetime_hours)
    freq_score = min(100.0, freq * 20.0)
    rules.append({
        "factor": "observation_frequency",
        "value": round(freq, 2),
        "raw_score": round(freq_score, 1),
        "weight": w["observation_frequency"],
        "weighted_points": round(freq_score * w["observation_frequency"], 1),
    })

    # 2. Radiative power (MW)
    frp_score = min(100.0, (max_frp / 120.0) * 100.0) if max_frp > 0 else 0.0
    rules.append({
        "factor": "radiative_power_mw",
        "value": round(max_frp, 2),
        "raw_score": round(frp_score, 1),
        "weight": w["radiative_power"],
        "weighted_points": round(frp_score * w["radiative_power"], 1),
    })

    # 3. Confidence [0, 1] -> [0, 100]
    conf_score = max(0.0, min(100.0, cluster_confidence * 100.0))
    rules.append({
        "factor": "cluster_confidence",
        "value": round(cluster_confidence, 2),
        "raw_score": round(conf_score, 1),
        "weight": w["confidence"],
        "weighted_points": round(conf_score * w["confidence"], 1),
    })

    # 4. Weather context (handles missing data gracefully)
    wind = (weather or {}).get("wind_speed_kmh")
    humidity = (weather or {}).get("relative_humidity_pct")
    if wind is None and humidity is None:
        weather_score = 30.0  # neutral fallback when weather is unavailable
        weather_val = "unavailable"
    else:
        w_pts = min(60.0, (wind or 0.0) * 1.5)
        h_pts = max(0.0, 40.0 - (humidity or 50.0) * 0.5)
        weather_score = min(100.0, w_pts + h_pts)
        weather_val = f"wind={wind}km/h, rh={humidity}%"
    rules.append({
        "factor": "weather_context",
        "value": weather_val,
        "raw_score": round(weather_score, 1),
        "weight": w["weather_risk"],
        "weighted_points": round(weather_score * w["weather_risk"], 1),
    })

    # 5. Persistence (hours active)
    pers_score = min(100.0, (lifetime_hours / 48.0) * 100.0)
    rules.append({
        "factor": "persistence_hours",
        "value": round(lifetime_hours, 1),
        "raw_score": round(pers_score, 1),
        "weight": w["persistence"],
        "weighted_points": round(pers_score * w["persistence"], 1),
    })

    total = round(sum(r["weighted_points"] for r in rules), 1)
    total = max(0.0, min(100.0, total))

    if total >= 75.0:
        tier = PriorityTier.CRITICAL
    elif total >= 55.0:
        tier = PriorityTier.HIGH
    elif total >= 35.0:
        tier = PriorityTier.MODERATE
    else:
        tier = PriorityTier.LOW

    return PriorityResult(
        score=total,
        tier=tier,
        rules_triggered=rules,
        disclaimer=(
            "Explainable rule-based heuristic score for monitoring prioritization; "
            "not a probability of danger or ML prediction."
        ),
    )
