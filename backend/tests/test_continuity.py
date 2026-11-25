from datetime import datetime, timedelta, timezone
from app.analytics.continuity import associate_incidents_to_events


def test_continuity_recovers_fragments_and_prevents_far_merge():
    t0 = datetime(2024, 8, 10, 12, 0, tzinfo=timezone.utc)
    incidents = [
        # Two fragments of the same fire (~4 km apart, 12h gap)
        {"id": "CL-1", "centroid_lat": 41.24, "centroid_lon": -123.46, "first_seen_at": t0, "last_seen_at": t0 + timedelta(hours=6), "hotspot_count": 30},
        {"id": "CL-2", "centroid_lat": 41.27, "centroid_lon": -123.44, "first_seen_at": t0 + timedelta(hours=18), "last_seen_at": t0 + timedelta(hours=24), "hotspot_count": 20},
        # Independent simultaneous fire ~45 km away
        {"id": "CL-3", "centroid_lat": 41.60, "centroid_lon": -123.10, "first_seen_at": t0, "last_seen_at": t0 + timedelta(hours=6), "hotspot_count": 15},
    ]
    events = associate_incidents_to_events(incidents, max_link_km=15.0, max_gap_hours=48.0)
    assert len(events) == 2
    assert events[0].member_incident_ids == ["CL-1", "CL-2"]
    assert events[0].total_hotspots == 50
    assert events[1].member_incident_ids == ["CL-3"]
