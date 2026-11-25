from datetime import datetime, timedelta, timezone
from experiments.flarepoint_event_validation.scripts.matching import match_incidents_to_reference


def _poly(lon0: float, lat0: float, d: float = 0.05) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[[lon0 - d, lat0 - d], [lon0 + d, lat0 - d], [lon0 + d, lat0 + d], [lon0 - d, lat0 + d], [lon0 - d, lat0 - d]]],
    }


def test_matching_fragmentation_and_unmatched():
    t0 = datetime(2024, 8, 10, 12, 0, tzinfo=timezone.utc)
    ms = int(t0.timestamp() * 1000)

    refs = [
        {
            "type": "Feature",
            "properties": {
                "attr_UniqueFireIdentifier": "2024-REF-1",
                "poly_IncidentName": "Alpha",
                "poly_GISAcres": 5000.0,
                "attr_FireDiscoveryDateTime": ms,
            },
            "geometry": _poly(-123.0, 41.0, d=0.05),
        },
        {
            "type": "Feature",
            "properties": {
                "attr_UniqueFireIdentifier": "2024-REF-2",
                "poly_IncidentName": "Beta",
                "poly_GISAcres": 1000.0,
                "attr_FireDiscoveryDateTime": ms,
            },
            "geometry": _poly(-121.0, 40.0, d=0.02),
        },
    ]

    # Two FlarePoint incidents inside REF-1 (fragmentation) + 1 unmatched far away
    fps = [
        {"id": "FP-1", "centroid_lat": 41.01, "centroid_lon": -123.01, "first_seen_at": t0, "last_seen_at": t0 + timedelta(hours=6), "obs_coords": [(41.01, -123.01)]},
        {"id": "FP-2", "centroid_lat": 40.99, "centroid_lon": -122.99, "first_seen_at": t0, "last_seen_at": t0 + timedelta(hours=6), "obs_coords": [(40.99, -122.99)]},
        {"id": "FP-3", "centroid_lat": 39.50, "centroid_lon": -124.00, "first_seen_at": t0, "last_seen_at": t0 + timedelta(hours=2), "obs_coords": [(39.50, -124.00)]},
    ]

    res = match_incidents_to_reference(fps, refs)
    assert res["event_metrics"]["true_positives_fp"] == 2
    assert res["event_metrics"]["unmatched_fp_count"] == 1
    assert res["event_metrics"]["matched_ref_count"] == 1
    assert res["event_metrics"]["unmatched_ref_count"] == 1
    assert res["fragmentation"]["fragmented_ref_count"] == 1
    assert res["spatial_metrics"]["median_perim_dist_km"] == 0.0
