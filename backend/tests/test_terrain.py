import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.terrain.derivatives import (
    circular_mean_deg,
    compute_curvature,
    compute_slope_aspect_horn,
    compute_tpi,
    compute_tri,
)
from app.terrain.extractor import extract_multiscale_terrain
from app.terrain.progression import classify_terrain_relative_displacement


def test_flat_surface_derivatives():
    dem = np.full((7, 7), 200.0)
    slope, aspect = compute_slope_aspect_horn(dem, cell_size_m=30.0)
    tri = compute_tri(dem)
    tpi = compute_tpi(dem)
    curv = compute_curvature(dem, cell_size_m=30.0)

    assert np.isclose(slope[3, 3], 0.0)
    assert np.isnan(aspect[3, 3])
    assert np.isclose(tri[3, 3], 0.0)
    assert np.isclose(tpi[3, 3], 0.0)
    assert np.isclose(curv[3, 3], 0.0)


def test_planar_slope_45_deg_east():
    # Elevation decreases toward East (+x) by 30m per 30m cell => 45 deg slope facing East (90 deg)
    y, x = np.mgrid[0:7, 0:7]
    dem = 500.0 - 30.0 * x
    slope, aspect = compute_slope_aspect_horn(dem, cell_size_m=30.0)
    assert np.isclose(slope[3, 3], 45.0, atol=0.1)
    assert np.isclose(aspect[3, 3], 270.0, atol=0.1) or np.isclose(aspect[3, 3], 90.0, atol=0.1)


def test_circular_mean_wraparound():
    angles = np.array([359.0, 1.0])
    cm = circular_mean_deg(angles)
    assert cm is not None
    assert cm < 2.0 or cm > 358.0


def test_multiscale_extraction_and_progression_classification():
    res = extract_multiscale_terrain(36.48989, 32.22333, scales_m=(250, 500, 1000))
    assert len(res["multiscale"]) == 3
    assert res["center_point"]["elevation_m"] > 0

    assert classify_terrain_relative_displacement(0.5, 0.0, 20.0, 15.0, 180.0) == "uphill-oriented"
    assert classify_terrain_relative_displacement(0.5, 180.0, -20.0, 15.0, 180.0) == "downhill-oriented"
    assert classify_terrain_relative_displacement(0.01, 0.0, 0.0, 15.0, 180.0) == "indeterminate"


def test_terrain_api_endpoints():
    with TestClient(app) as client:
        src = client.get("/api/v1/terrain/sources")
        assert src.status_code == 200
        assert src.json()["dataset"] == "Copernicus DEM GLO-30"

        inc_id = client.get("/api/v1/incidents").json()[0]["id"]
        ter = client.get(f"/api/v1/incidents/{inc_id}/terrain")
        assert ter.status_code == 200
        assert len(ter.json()["multiscale"]) == 4

        prog = client.get(f"/api/v1/incidents/{inc_id}/progression")
        assert prog.status_code == 200
        assert "not a direct estimate of fire-front movement" in prog.json()["disclaimer"].lower()
