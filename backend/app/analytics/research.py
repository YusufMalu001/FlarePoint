from dataclasses import dataclass
from typing import Any
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestRegressor


@dataclass
class AnomalyResult:
    is_anomaly: bool
    anomaly_score: float
    method: str
    explanation: str


@dataclass
class ForecastResult:
    target: str
    horizon_hours: int
    predicted_count: float
    interval_low: float
    interval_high: float
    baseline_persistence: float
    model_mae: float | None
    baseline_mae: float | None
    interval_coverage: float | None
    disclaimer: str = (
        "Short-term satellite detection activity forecast; "
        "NOT a physical fire-spread prediction."
    )


def detect_window_anomalies(
    windows: list[dict[str, float]],
    contamination: float = 0.1,
) -> list[AnomalyResult]:
    """
    Experiment 2: Detect statistical anomalies in time-window activity
    using Isolation Forest (fallback to MAD z-score for small samples).
    """
    if not windows:
        return []

    features = np.array(
        [[w["hotspot_count"], w["max_frp"], w["affected_area_km2"]] for w in windows],
        dtype=float,
    )

    if len(windows) < 6:
        med = np.median(features[:, 1])
        mad = np.median(np.abs(features[:, 1] - med)) or 1.0
        results = []
        for row in features:
            z = abs(row[1] - med) / (1.4826 * mad)
            is_anom = bool(z > 3.0)
            results.append(
                AnomalyResult(
                    is_anomaly=is_anom,
                    anomaly_score=round(float(z), 3),
                    method="robust_mad_frp",
                    explanation="Statistical FRP outlier (not necessarily a high-risk fire)."
                    if is_anom
                    else "Within normal observed range.",
                )
            )
        return results

    clf = IsolationForest(contamination=contamination, random_state=42)
    preds = clf.fit_predict(features)
    scores = -clf.score_samples(features)
    return [
        AnomalyResult(
            is_anomaly=bool(p == -1),
            anomaly_score=round(float(s), 3),
            method="isolation_forest",
            explanation="Multivariate statistical outlier in (count, max_frp, area)."
            if p == -1
            else "Within normal observed range.",
        )
        for p, s in zip(preds, scores)
    ]


def forecast_next_window_activity(
    counts: list[int],
    frps: list[float],
    horizon_hours: int = 6,
) -> ForecastResult:
    """
    Experiments 3 & 4: Temporal-split activity forecasting with conformal-style
    empirical residual intervals, compared against a persistence baseline.
    """
    if len(counts) < 5:
        last = float(counts[-1]) if counts else 0.0
        return ForecastResult(
            target="next_window_hotspot_count",
            horizon_hours=horizon_hours,
            predicted_count=last,
            interval_low=max(0.0, last - 2.0),
            interval_high=last + 2.0,
            baseline_persistence=last,
            model_mae=None,
            baseline_mae=None,
            interval_coverage=None,
        )

    # Build lagged supervised pairs (t-2, t-1 -> t) without future leakage
    X, y, base_preds = [], [], []
    for i in range(2, len(counts)):
        X.append([counts[i - 1], counts[i - 2], frps[i - 1], frps[i - 2]])
        y.append(float(counts[i]))
        base_preds.append(float(counts[i - 1]))

    X_arr = np.array(X, dtype=float)
    y_arr = np.array(y, dtype=float)
    base_arr = np.array(base_preds, dtype=float)

    split = max(2, int(len(X_arr) * 0.7))
    X_train, X_val = X_arr[:split], X_arr[split:]
    y_train, y_val = y_arr[:split], y_arr[split:]
    base_val = base_arr[split:]

    model = RandomForestRegressor(n_estimators=50, max_depth=4, random_state=42)
    model.fit(X_train, y_train)

    if len(X_val) > 0:
        val_preds = model.predict(X_val)
        residuals = np.abs(y_val - val_preds)
        q90 = float(np.quantile(residuals, 0.9)) if len(residuals) > 0 else 2.0
        model_mae = round(float(np.mean(residuals)), 3)
        baseline_mae = round(float(np.mean(np.abs(y_val - base_val))), 3)
        coverage = round(float(np.mean(residuals <= q90)), 3)
    else:
        q90 = 2.0
        model_mae = None
        baseline_mae = None
        coverage = None

    next_x = np.array([[counts[-1], counts[-2], frps[-1], frps[-2]]], dtype=float)
    pred = float(model.predict(next_x)[0])
    return ForecastResult(
        target="next_window_hotspot_count",
        horizon_hours=horizon_hours,
        predicted_count=round(max(0.0, pred), 2),
        interval_low=round(max(0.0, pred - q90), 2),
        interval_high=round(pred + q90, 2),
        baseline_persistence=float(counts[-1]),
        model_mae=model_mae,
        baseline_mae=baseline_mae,
        interval_coverage=coverage,
    )
