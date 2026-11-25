from unittest.mock import patch
from fastapi.testclient import TestClient

from app.domain.models import DataOrigin
from app.main import app
from app.pipelines.normalize import normalize_confidence, validate_and_normalize_row


def test_normalize_confidence():
    assert normalize_confidence("h") == 0.95
    assert normalize_confidence("n") == 0.65
    assert normalize_confidence("l") == 0.30
    assert normalize_confidence("80") == 0.80
    assert normalize_confidence(None) is None


def test_validation_and_no_invented_values():
    valid_minimal = {
        "latitude": "36.48989",
        "longitude": "32.22333",
        "acq_date": "2026-11-24",
        "acq_time": "40",  # tests zero-padding to 0040
        "satellite": "N20",
    }
    res = validate_and_normalize_row(valid_minimal, "VIIRS_SNPP_NRT", DataOrigin.SIMULATED_DEMO)
    assert res.is_valid is True
    assert res.observation is not None
    assert res.observation.acq_time == "0040"
    assert res.observation.frp is None  # not invented as 0
    assert res.observation.brightness is None

    bad_lat = {**valid_minimal, "latitude": "95.0"}
    res_bad = validate_and_normalize_row(bad_lat, "VIIRS_SNPP_NRT", DataOrigin.SIMULATED_DEMO)
    assert res_bad.is_valid is False
    assert any("latitude_out_of_bounds" in e for e in res_bad.errors)

    bad_frp = {**valid_minimal, "frp": "-5.0"}
    res_frp = validate_and_normalize_row(bad_frp, "VIIRS_SNPP_NRT", DataOrigin.SIMULATED_DEMO)
    assert res_frp.is_valid is False
    assert any("negative_frp" in e for e in res_frp.errors)


def test_idempotency_and_api_filtering():
    with TestClient(app) as client:
        # Health & sources
        h = client.get("/api/v1/health")
        assert h.status_code == 200
        assert h.json()["mode"] == "SIMULATED_DEMO"

        sources = client.get("/api/v1/sources")
        assert sources.status_code == 200
        assert len(sources.json()["sources"]) == 3

        # Triggering demo ingest twice in a row should be idempotent
        r1 = client.post("/api/v1/ingest/run", json={"day_range": 3, "force_demo": True})
        assert r1.status_code == 200
        r2 = client.post("/api/v1/ingest/run", json={"day_range": 3, "force_demo": True})
        assert r2.status_code == 200
        assert r2.json()["records_duplicate"] > 0

        # Pagination & bbox filtering
        obs_page = client.get("/api/v1/observations?limit=5&offset=0&data_origin=SIMULATED_DEMO")
        assert obs_page.status_code == 200
        assert len(obs_page.json()["items"]) <= 5

        bbox_obs = client.get("/api/v1/observations?bbox=30,34,35,38")
        assert bbox_obs.status_code == 200
        for item in bbox_obs.json()["items"]:
            assert 30.0 <= item["longitude"] <= 35.0
            assert 34.0 <= item["latitude"] <= 38.0

        # Invalid bbox returns 422
        bad_bbox = client.get("/api/v1/observations?bbox=invalid")
        assert bad_bbox.status_code == 422


def test_mocked_firms_adapter():
    sample_csv_rows = [
        {
            "latitude": "36.50",
            "longitude": "32.20",
            "bright_ti4": "340.1",
            "acq_date": "2026-11-24",
            "acq_time": "1200",
            "satellite": "N20",
            "confidence": "h",
            "frp": "55.2",
            "daynight": "D",
        }
    ]
    with patch("app.adapters.firms.FirmsAdapter.fetch_area_csv", return_value=sample_csv_rows):
        from app.adapters.firms import FirmsAdapter

        rows = FirmsAdapter().fetch_area_csv(source="VIIRS_SNPP_NRT", bbox="30,34,35,38", day_range=1)
        assert len(rows) == 1
        assert rows[0]["frp"] == "55.2"
