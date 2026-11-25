from datetime import datetime, timedelta, timezone

from app.analytics.clustering import cluster_observations_spatiotemporal
from app.analytics.prioritization import compute_priority
from app.analytics.tracking import compute_association_score, evaluate_lifecycle_status
from app.storage.models import IncidentModel, ObservationModel


def _make_obs(id_str: str, lat: float, lon: float, ts: datetime, frp: float = 25.0) -> ObservationModel:
    return ObservationModel(
        id=id_str,
        ingestion_run_id="run-1",
        source_sensor="VIIRS_SNPP_NRT",
        satellite="N20",
        instrument="VIIRS",
        acq_date=ts.strftime("%Y-%m-%d"),
        acq_time=ts.strftime("%H%M"),
        acq_timestamp=ts,
        latitude=lat,
        longitude=lon,
        brightness=330.0,
        frp=frp,
        confidence_raw="h",
        confidence_norm=0.95,
        daynight="D",
        raw_payload={},
        dedup_hash=f"hash-{id_str}",
        data_origin="SIMULATED_DEMO",
    )


def test_cluster_formation_and_noise():
    now = datetime.now(timezone.utc)
    obs = [
        _make_obs("1", 36.500, 32.200, now),
        _make_obs("2", 36.505, 32.205, now + timedelta(minutes=10)),
        _make_obs("3", 36.508, 32.202, now + timedelta(minutes=20)),
        # Isolated noise point far away
        _make_obs("4", 10.000, 10.000, now),
    ]
    res = cluster_observations_spatiotemporal(obs, eps_km=5.0, min_samples=3)
    assert len(res.clusters) == 1
    assert res.clusters[0].observation_count == 3
    assert "4" in res.noise_observation_ids


def test_temporal_separation_prevents_merging():
    t0 = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=36)  # > 24h gap at exact same coordinates
    obs = [
        _make_obs("a1", 36.500, 32.200, t0),
        _make_obs("a2", 36.502, 32.202, t0 + timedelta(hours=1)),
        _make_obs("a3", 36.504, 32.201, t0 + timedelta(hours=2)),
        _make_obs("b1", 36.500, 32.200, t1),
        _make_obs("b2", 36.502, 32.202, t1 + timedelta(hours=1)),
        _make_obs("b3", 36.504, 32.201, t1 + timedelta(hours=2)),
    ]
    res = cluster_observations_spatiotemporal(obs, eps_km=5.0, min_samples=3, max_temporal_gap_hours=24.0)
    assert len(res.clusters) == 2


def test_incident_non_association_beyond_radius():
    now = datetime.now(timezone.utc)
    obs = [
        _make_obs("1", 36.500, 32.200, now),
        _make_obs("2", 36.502, 32.202, now),
        _make_obs("3", 36.504, 32.201, now),
    ]
    cl = cluster_observations_spatiotemporal(obs).clusters[0]
    far_incident = IncidentModel(
        id="inc-far",
        persistent_key="FP-FAR",
        first_seen_at=now - timedelta(hours=2),
        last_seen_at=now - timedelta(hours=1),
        status="ACTIVE",
        centroid_lat=38.000,  # > 150km away
        centroid_lon=34.000,
        footprint_geojson={},
        affected_area_km2=1.0,
        data_origin="SIMULATED_DEMO",
    )
    assert compute_association_score(cl, far_incident, max_radius_km=10.0) is None


def test_lifecycle_transitions():
    now = datetime.now(timezone.utc)
    assert evaluate_lifecycle_status("NEWLY_OBSERVED", now, now=now, has_new_detections=True) == "ACTIVE"
    assert evaluate_lifecycle_status("ACTIVE", now - timedelta(hours=30), now=now, has_new_detections=False) == "DORMANT"
    assert evaluate_lifecycle_status("DORMANT", now - timedelta(hours=30), now=now, has_new_detections=True) == "RE_OBSERVED"
    assert evaluate_lifecycle_status("DORMANT", now - timedelta(hours=80), now=now, has_new_detections=False) == "CLOSED"


def test_priority_handles_missing_weather():
    res = compute_priority(
        hotspot_count=10,
        max_frp=60.0,
        affected_area_km2=5.0,
        cluster_confidence=0.85,
        weather=None,
        lifetime_hours=12.0,
    )
    assert 0.0 <= res.score <= 100.0
    assert "not a probability of danger" in res.disclaimer.lower()
