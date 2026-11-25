from experiments.flarepoint_terrain_fire_study.scripts.study_lib import (
    benjamini_hochberg_fdr,
    classify_aspect_sector,
    classify_elevation,
    classify_slope,
    kruskal_by_group,
)


def test_terrain_classification_and_flat_aspect_exclusion():
    elev_edges = [0, 250, 500, 750, 1000, 1500, 2000, 5000]
    assert classify_elevation(300.0, elev_edges) == "250-500m"
    assert classify_elevation(2200.0, elev_edges) == "2000m+"

    slope_edges = [0, 5, 15, 30, 45, 90]
    assert classify_slope(12.0, slope_edges) == "5-15deg"

    # Flat terrain (< 5 deg) must not receive an arbitrary compass aspect
    assert classify_aspect_sector(180.0, 2.0, flat_threshold_deg=5.0) == "FLAT_UNDEFINED"
    assert classify_aspect_sector(359.0, 15.0, flat_threshold_deg=5.0) == "N"
    assert classify_aspect_sector(225.0, 15.0, flat_threshold_deg=5.0) == "SW"


def test_benjamini_hochberg_fdr():
    adj = benjamini_hochberg_fdr([0.01, 0.04, 0.20, 0.50])
    assert adj == [0.04, 0.08, 0.266667, 0.5]


def test_kruskal_by_group():
    res = kruskal_by_group([1, 2, 1, 10, 12, 11], ["A", "A", "A", "B", "B", "B"])
    assert res["groups"] == 2
    assert res["p_value"] < 0.06


def test_morans_i_spatial_autocorrelation():
    import numpy as np
    from experiments.flarepoint_terrain_fire_study.audit.run_audit import morans_i

    coords = np.array([[0.0, 0.0], [10000.0, 0.0], [20000.0, 0.0], [100000.0, 0.0], [110000.0, 0.0]])
    vals = np.array([10.0, 10.0, 10.0, 0.0, 0.0])
    res = morans_i(vals, coords, max_dist_m=15000.0, permutations=99)
    assert res["morans_i"] > 0.5
    assert res["n"] == 5
