import math
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

import numpy as np
from shapely.geometry import MultiPoint, mapping
from sklearn.cluster import DBSCAN

from app.core.config import settings
from app.storage.models import ObservationModel

EARTH_RADIUS_KM = 6371.0088


@dataclass
class ClusterCandidate:
    """Derived spatial-temporal cluster of satellite observations (not a confirmed wildfire)."""

    cluster_id: str
    member_observation_ids: list[str]
    observations: list[ObservationModel]
    centroid_lat: float
    centroid_lon: float
    observation_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    footprint_geojson: dict
    affected_area_km2: float
    density_per_km2: float


@dataclass
class ClusteringResult:
    clusters: list[ClusterCandidate]
    noise_observation_ids: list[str]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points in kilometers."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def compute_footprint(observations: Sequence[ObservationModel]) -> tuple[dict, float]:
    """
    Compute convex hull / buffered footprint GeoJSON and upper-bound affected area (km^2).
    Note: This is an affected-area proxy, NOT an actual burned perimeter.
    """
    pts = [(obs.longitude, obs.latitude) for obs in observations]
    geom = MultiPoint(pts).convex_hull.buffer(0.005)
    centroid = geom.centroid
    lat_km = 111.32
    lon_km = 111.32 * max(0.1, math.cos(math.radians(centroid.y)))
    area_km2 = max(0.01, round(geom.area * lat_km * lon_km, 2))
    return mapping(geom), area_km2


def cluster_observations_spatiotemporal(
    observations: Sequence[ObservationModel],
    eps_km: float | None = None,
    min_samples: int | None = None,
    max_temporal_gap_hours: float = 24.0,
) -> ClusteringResult:
    """
    Phases A & B: Spatial DBSCAN (Haversine) followed by temporal-gap splitting
    so geographically close but temporally unrelated detections are not merged.
    """
    if not observations:
        return ClusteringResult(clusters=[], noise_observation_ids=[])

    eps = (eps_km or settings.dbscan_eps_km) / EARTH_RADIUS_KM
    min_pts = min_samples or settings.dbscan_min_samples

    coords_rad = np.radians([[obs.latitude, obs.longitude] for obs in observations])
    labels = DBSCAN(eps=eps, min_samples=min_pts, metric="haversine").fit_predict(coords_rad)

    spatial_groups: dict[int, list[ObservationModel]] = {}
    noise_ids: list[str] = []
    for obs, label in zip(observations, labels):
        if label == -1:
            noise_ids.append(obs.id)
        else:
            spatial_groups.setdefault(int(label), []).append(obs)

    clusters: list[ClusterCandidate] = []
    cluster_idx = 0

    for _, group in spatial_groups.items():
        # Sort by timestamp and split if gap > max_temporal_gap_hours
        sorted_obs = sorted(group, key=lambda o: o.acq_timestamp)
        sub_groups: list[list[ObservationModel]] = [[sorted_obs[0]]]
        for obs in sorted_obs[1:]:
            gap_h = (obs.acq_timestamp - sub_groups[-1][-1].acq_timestamp).total_seconds() / 3600.0
            if gap_h > max_temporal_gap_hours:
                sub_groups.append([obs])
            else:
                sub_groups[-1].append(obs)

        for sg in sub_groups:
            if len(sg) < min_pts:
                noise_ids.extend(o.id for o in sg)
                continue
            cluster_idx += 1
            c_lat = sum(o.latitude for o in sg) / len(sg)
            c_lon = sum(o.longitude for o in sg) / len(sg)
            footprint, area_km2 = compute_footprint(sg)
            clusters.append(
                ClusterCandidate(
                    cluster_id=f"CL-{cluster_idx:04d}",
                    member_observation_ids=[o.id for o in sg],
                    observations=sg,
                    centroid_lat=c_lat,
                    centroid_lon=c_lon,
                    observation_count=len(sg),
                    first_seen_at=sg[0].acq_timestamp,
                    last_seen_at=sg[-1].acq_timestamp,
                    footprint_geojson=footprint,
                    affected_area_km2=area_km2,
                    density_per_km2=round(len(sg) / area_km2, 2),
                )
            )

    return ClusteringResult(clusters=clusters, noise_observation_ids=noise_ids)
