from fastapi.testclient import TestClient

from app.domain.models import DataOrigin
from app.main import app
from app.pipelines.normalize import normalize_confidence, normalize_row


def test_normalize_confidence():
    assert normalize_confidence("h") == 0.95
    assert normalize_confidence("n") == 0.65
    assert normalize_confidence("l") == 0.30
    assert normalize_confidence("80") == 0.80


def test_normalize_row_validation():
    valid = {
        "latitude": "36.48989",
        "longitude": "32.22333",
        "bright_ti4": "345.2",
        "acq_date": "2026-11-24",
        "acq_time": "1040",
        "satellite": "N20",
        "confidence": "h",
        "frp": "48.5",
        "daynight": "D",
    }
    obs = normalize_row(valid, "VIIRS_SNPP_NRT", DataOrigin.SIMULATED_DEMO)
    assert obs is not None
    assert obs.confidence_norm == 0.95
    assert obs.frp == 48.5

    invalid_lat = {**valid, "latitude": "999.0"}
    assert normalize_row(invalid_lat, "VIIRS_SNPP_NRT", DataOrigin.SIMULATED_DEMO) is None


def test_api_end_to_end():
    with TestClient(app) as client:
        h = client.get("/api/v1/health")
        assert h.status_code == 200
        assert h.json()["mode"] == "SIMULATED_DEMO"
        assert h.json()["incident_count"] >= 1

        incidents = client.get("/api/v1/incidents").json()
        assert len(incidents) >= 1
        first_id = incidents[0]["id"]

        detail = client.get(f"/api/v1/incidents/{first_id}")
        assert detail.status_code == 200
        assert "rules" in detail.json()["priority_explanation"]

        obs = client.get(f"/api/v1/incidents/{first_id}/observations")
        assert obs.status_code == 200
        assert len(obs.json()) >= 3

        timeline = client.get(f"/api/v1/incidents/{first_id}/timeline")
        assert timeline.status_code == 200
