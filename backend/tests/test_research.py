from app.analytics.research import detect_window_anomalies, forecast_next_window_activity


def test_anomaly_detection_identifies_spike():
    windows = [
        {"hotspot_count": 5.0, "max_frp": 20.0, "affected_area_km2": 2.0},
        {"hotspot_count": 6.0, "max_frp": 22.0, "affected_area_km2": 2.2},
        {"hotspot_count": 5.0, "max_frp": 19.0, "affected_area_km2": 1.9},
        {"hotspot_count": 7.0, "max_frp": 24.0, "affected_area_km2": 2.4},
        {"hotspot_count": 6.0, "max_frp": 21.0, "affected_area_km2": 2.1},
        {"hotspot_count": 5.0, "max_frp": 20.0, "affected_area_km2": 2.0},
        {"hotspot_count": 45.0, "max_frp": 320.0, "affected_area_km2": 18.0},
    ]
    res = detect_window_anomalies(windows, contamination=0.15)
    assert len(res) == 7
    assert res[-1].is_anomaly is True


def test_temporal_forecast_and_uncertainty_intervals():
    counts = [4, 6, 8, 10, 12, 14, 15, 13, 11, 9]
    frps = [20.0, 25.0, 35.0, 45.0, 55.0, 60.0, 62.0, 50.0, 40.0, 30.0]
    res = forecast_next_window_activity(counts, frps, horizon_hours=6)
    assert res.interval_low <= res.predicted_count <= res.interval_high
    assert res.model_mae is not None
    assert res.baseline_mae is not None
    assert "not a physical fire-spread" in res.disclaimer.lower()
