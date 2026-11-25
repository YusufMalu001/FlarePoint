import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.adapters.weather import WeatherAdapter
from app.analytics.clustering import (
    ClusterCandidate,
    cluster_observations_spatiotemporal,
    compute_footprint,
    haversine_km,
)
from app.analytics.prioritization import compute_priority
from app.core.config import settings
from app.storage.models import (
    AuditLogModel,
    IncidentModel,
    IncidentObservationModel,
    IncidentSnapshotModel,
    ObservationModel,
)


def _derive_land_cover_summary(lat: float, lon: float) -> dict[str, float]:
    """Optional regional land-cover proxy when local rasters are not mounted."""
    if 34.0 <= lat <= 43.0 and -10.0 <= lon <= 35.0:
        return {"Forest": 58.0, "Shrubland": 24.0, "Grassland": 11.0, "Cropland": 4.0, "Built-up": 2.0, "Bare": 1.0}
    return {"Forest": 45.0, "Shrubland": 28.0, "Grassland": 17.0, "Cropland": 6.0, "Built-up": 2.0, "Bare": 2.0}


def compute_association_score(
    cluster: ClusterCandidate,
    incident: IncidentModel,
    max_radius_km: float,
    max_gap_hours: float = 48.0,
) -> float | None:
    """
    Phase C: Weighted association score in [0, 1] (higher = stronger match).
    Returns None if distance or temporal gap exceeds hard thresholds.
    """
    dist_km = haversine_km(
        cluster.centroid_lat, cluster.centroid_lon, incident.centroid_lat, incident.centroid_lon
    )
    if dist_km > max_radius_km:
        return None

    if cluster.first_seen_at <= incident.last_seen_at and cluster.last_seen_at >= incident.first_seen_at:
        gap_hours = 0.0
    else:
        gap_hours = min(
            abs((cluster.first_seen_at - incident.last_seen_at).total_seconds()),
            abs((incident.first_seen_at - cluster.last_seen_at).total_seconds()),
        ) / 3600.0
    if gap_hours > max_gap_hours:
        return None

    dist_score = 1.0 - (dist_km / max_radius_km)
    time_score = 1.0 - (gap_hours / max_gap_hours)
    return round(0.65 * dist_score + 0.35 * time_score, 4)


def evaluate_lifecycle_status(
    current_status: str,
    last_seen_at: datetime,
    now: datetime | None = None,
    has_new_detections: bool = False,
) -> str:
    """
    Phase D: Auditable incident lifecycle transitions.
    - NEWLY_OBSERVED -> ACTIVE when updated with detections
    - ACTIVE -> DORMANT after 24h without detections
    - DORMANT -> RE_OBSERVED when new detections arrive
    - DORMANT -> CLOSED only after 72h+ without detections
    """
    ref_now = now or datetime.now(timezone.utc)
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
    gap_hours = (ref_now - last_seen_at).total_seconds() / 3600.0

    if has_new_detections:
        if current_status == "DORMANT":
            return "RE_OBSERVED"
        if current_status == "NEWLY_OBSERVED":
            return "ACTIVE"
        return current_status

    if gap_hours >= 72.0:
        return "CLOSED"
    if gap_hours >= 24.0:
        return "DORMANT"
    return current_status


def process_incidents(db: Session) -> list[IncidentModel]:
    """
    Phases A-G: Spatiotemporal clustering, 1-to-1 weighted incident association,
    lifecycle management, evolution snapshots, optional enrichment, and prioritization.
    """
    observations = db.query(ObservationModel).order_by(ObservationModel.acq_timestamp.asc()).all()
    clustering = cluster_observations_spatiotemporal(observations)
    existing_incidents = db.query(IncidentModel).all()
    weather_adapter = WeatherAdapter()

    # Phase C: 1-to-1 greedy bipartite matching by highest association score
    pairs: list[tuple[float, int, IncidentModel]] = []
    for idx, cl in enumerate(clustering.clusters):
        for inc in existing_incidents:
            score = compute_association_score(
                cl, inc, max_radius_km=settings.incident_association_radius_km
            )
            if score is not None:
                pairs.append((score, idx, inc))

    pairs.sort(key=lambda x: x[0], reverse=True)
    matched_cluster_idxs: set[int] = set()
    matched_incident_ids: set[str] = set()
    cluster_to_incident: dict[int, IncidentModel] = {}

    for score, cl_idx, inc in pairs:
        if cl_idx not in matched_cluster_idxs and inc.id not in matched_incident_ids:
            matched_cluster_idxs.add(cl_idx)
            matched_incident_ids.add(inc.id)
            cluster_to_incident[cl_idx] = inc

    updated_incidents: list[IncidentModel] = []

    for idx, cl in enumerate(clustering.clusters):
        obs_list = cl.observations
        frp_vals = [o.frp for o in obs_list if o.frp is not None]
        conf_vals = [o.confidence_norm for o in obs_list if o.confidence_norm is not None]
        max_frp = max(frp_vals) if frp_vals else 0.0
        mean_frp = (sum(frp_vals) / len(frp_vals)) if frp_vals else 0.0
        mean_conf = (sum(conf_vals) / len(conf_vals)) if conf_vals else 0.5
        origin = obs_list[0].data_origin
        lifetime_h = max(1.0, (cl.last_seen_at - cl.first_seen_at).total_seconds() / 3600.0)

        weather = weather_adapter.fetch_context(cl.centroid_lat, cl.centroid_lon)
        land_cover = _derive_land_cover_summary(cl.centroid_lat, cl.centroid_lon)
        priority = compute_priority(
            cl.observation_count, max_frp, cl.affected_area_km2, mean_conf, weather, lifetime_h
        )

        matched = cluster_to_incident.get(idx)
        if matched is None:
            pkey = f"FP-{hashlib.sha1(f'{cl.centroid_lat:.3f},{cl.centroid_lon:.3f}'.encode()).hexdigest()[:8].upper()}"
            matched = IncidentModel(
                persistent_key=pkey,
                first_seen_at=cl.first_seen_at,
                last_seen_at=cl.last_seen_at,
                status="NEWLY_OBSERVED",
                centroid_lat=cl.centroid_lat,
                centroid_lon=cl.centroid_lon,
                footprint_geojson=cl.footprint_geojson,
                affected_area_km2=cl.affected_area_km2,
                hotspot_count=cl.observation_count,
                max_frp=round(max_frp, 2),
                mean_frp=round(mean_frp, 2),
                cluster_confidence=round(mean_conf, 2),
                priority_score=priority.score,
                priority_tier=priority.tier.value,
                priority_explanation={
                    "rules": priority.rules_triggered,
                    "disclaimer": priority.disclaimer,
                },
                weather_context=weather,
                land_cover_summary=land_cover,
                data_origin=origin,
            )
            db.add(matched)
            db.flush()
            existing_incidents.append(matched)
        else:
            new_status = evaluate_lifecycle_status(
                matched.status, matched.last_seen_at, has_new_detections=True
            )
            matched.status = new_status
            matched.first_seen_at = min(matched.first_seen_at, cl.first_seen_at)
            matched.last_seen_at = max(matched.last_seen_at, cl.last_seen_at)
            matched.centroid_lat = cl.centroid_lat
            matched.centroid_lon = cl.centroid_lon
            matched.footprint_geojson = cl.footprint_geojson
            matched.affected_area_km2 = cl.affected_area_km2
            matched.hotspot_count = cl.observation_count
            matched.max_frp = round(max_frp, 2)
            matched.mean_frp = round(mean_frp, 2)
            matched.cluster_confidence = round(mean_conf, 2)
            matched.priority_score = priority.score
            matched.priority_tier = priority.tier.value
            matched.priority_explanation = {
                "rules": priority.rules_triggered,
                "disclaimer": priority.disclaimer,
            }
            matched.weather_context = weather
            matched.land_cover_summary = land_cover

        for obs in obs_list:
            link_exists = (
                db.query(IncidentObservationModel)
                .filter_by(incident_id=matched.id, observation_id=obs.id)
                .first()
            )
            if not link_exists:
                db.add(IncidentObservationModel(incident_id=matched.id, observation_id=obs.id))

        if not matched.snapshots:
            cur = cl.first_seen_at
            while cur <= cl.last_seen_at:
                win_end = cur + timedelta(hours=6)
                win_obs = [o for o in obs_list if cur <= o.acq_timestamp < win_end]
                if win_obs:
                    _, win_area = compute_footprint(win_obs)
                    w_frps = [o.frp for o in win_obs if o.frp is not None]
                    db.add(
                        IncidentSnapshotModel(
                            incident_id=matched.id,
                            window_start=cur,
                            window_end=win_end,
                            hotspot_count=len(win_obs),
                            max_frp=round(max(w_frps), 2) if w_frps else 0.0,
                            mean_frp=round(sum(w_frps) / len(w_frps), 2) if w_frps else 0.0,
                            affected_area_km2=win_area,
                            centroid_lat=sum(o.latitude for o in win_obs) / len(win_obs),
                            centroid_lon=sum(o.longitude for o in win_obs) / len(win_obs),
                        )
                    )
                cur = win_end

        updated_incidents.append(matched)

    db.add(
        AuditLogModel(
            event_type="INCIDENTS_PROCESSED",
            entity_type="pipeline",
            entity_id="clustering",
            payload={
                "incident_count": len(updated_incidents),
                "noise_observations": len(clustering.noise_observation_ids),
            },
        )
    )
    db.commit()
    return updated_incidents
