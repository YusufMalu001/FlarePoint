import hashlib
from datetime import timedelta
from sqlalchemy.orm import Session

from app.adapters.weather import WeatherAdapter
from app.analytics.clustering import cluster_observations, compute_footprint, haversine_km
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
    """
    Deterministic regional land-cover breakdown placeholder when external
    rasters (e.g. ESA WorldCover) are not mounted locally.
    """
    if 34.0 <= lat <= 43.0 and -10.0 <= lon <= 35.0:
        return {"Forest": 58.0, "Shrubland": 24.0, "Grassland": 11.0, "Cropland": 4.0, "Built-up": 2.0, "Bare": 1.0}
    return {"Forest": 45.0, "Shrubland": 28.0, "Grassland": 17.0, "Cropland": 6.0, "Built-up": 2.0, "Bare": 2.0}


def process_incidents(db: Session) -> list[IncidentModel]:
    """
    Stages 3-6: Cluster observations, associate with persistent incidents,
    record evolution snapshots, enrich with weather, and compute priority.
    """
    observations = db.query(ObservationModel).order_by(ObservationModel.acq_timestamp.asc()).all()
    clusters = cluster_observations(observations)
    existing_incidents = db.query(IncidentModel).all()
    weather_adapter = WeatherAdapter()
    updated_incidents: list[IncidentModel] = []

    for _, obs_list in clusters.items():
        c_lat = sum(o.latitude for o in obs_list) / len(obs_list)
        c_lon = sum(o.longitude for o in obs_list) / len(obs_list)
        first_seen = min(o.acq_timestamp for o in obs_list)
        last_seen = max(o.acq_timestamp for o in obs_list)
        frp_vals = [o.frp for o in obs_list if o.frp is not None]
        conf_vals = [o.confidence_norm for o in obs_list if o.confidence_norm is not None]
        max_frp = max(frp_vals) if frp_vals else 0.0
        mean_frp = (sum(frp_vals) / len(frp_vals)) if frp_vals else 0.0
        mean_conf = (sum(conf_vals) / len(conf_vals)) if conf_vals else 0.5
        footprint, area_km2 = compute_footprint(obs_list)
        origin = obs_list[0].data_origin

        # Stage 3-4: Associate with nearest existing incident within radius
        matched: IncidentModel | None = None
        best_dist = settings.incident_association_radius_km
        for inc in existing_incidents:
            dist = haversine_km(c_lat, c_lon, inc.centroid_lat, inc.centroid_lon)
            if dist <= best_dist:
                best_dist = dist
                matched = inc

        weather = weather_adapter.fetch_context(c_lat, c_lon)
        land_cover = _derive_land_cover_summary(c_lat, c_lon)
        priority = compute_priority(len(obs_list), max_frp, area_km2, mean_conf, weather)

        if matched is None:
            pkey = f"FP-{hashlib.sha1(f'{c_lat:.3f},{c_lon:.3f}'.encode()).hexdigest()[:8].upper()}"
            matched = IncidentModel(
                persistent_key=pkey,
                first_seen_at=first_seen,
                last_seen_at=last_seen,
                status="ACTIVE",
                centroid_lat=c_lat,
                centroid_lon=c_lon,
                footprint_geojson=footprint,
                affected_area_km2=area_km2,
                hotspot_count=len(obs_list),
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
            matched.first_seen_at = min(matched.first_seen_at, first_seen)
            matched.last_seen_at = max(matched.last_seen_at, last_seen)
            matched.centroid_lat = c_lat
            matched.centroid_lon = c_lon
            matched.footprint_geojson = footprint
            matched.affected_area_km2 = area_km2
            matched.hotspot_count = len(obs_list)
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

        # Link observations idempotently
        for obs in obs_list:
            link_exists = (
                db.query(IncidentObservationModel)
                .filter_by(incident_id=matched.id, observation_id=obs.id)
                .first()
            )
            if not link_exists:
                db.add(IncidentObservationModel(incident_id=matched.id, observation_id=obs.id))

        # Stage 5: Build 6-hour evolution snapshots if none exist yet
        if not matched.snapshots:
            cur = first_seen
            while cur <= last_seen:
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
            payload={"incident_count": len(updated_incidents)},
        )
    )
    db.commit()
    return updated_incidents
