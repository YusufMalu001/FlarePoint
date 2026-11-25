import math
from typing import Sequence

import numpy as np
from shapely.geometry import MultiPoint, mapping
from sklearn.cluster import DBSCAN

from app.core.config import settings
from app.storage.models import ObservationModel

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points in kilometers."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def cluster_observations(
    observations: Sequence[ObservationModel],
    eps_km: float | None = None,
    min_samples: int | None = None,
) -> dict[int, list[ObservationModel]]:
    """Stage 1-2: Spatial clustering using DBSCAN with Haversine metric."""
    if not observations:
        return {}

    eps = (eps_km or settings.dbscan_eps_km) / EARTH_RADIUS_KM
    min_pts = min_samples or settings.dbscan_min_samples

    coords_rad = np.radians([[obs.latitude, obs.longitude] for obs in observations])
    labels = DBSCAN(eps=eps, min_samples=min_pts, metric="haversine").fit_predict(coords_rad)

    clusters: dict[int, list[ObservationModel]] = {}
    for obs, label in zip(observations, labels):
        if label == -1:
            continue
        clusters.setdefault(int(label), []).append(obs)
    return clusters


def compute_footprint(observations: Sequence[ObservationModel]) -> tuple[dict, float]:
    """
    Compute convex hull / buffered footprint GeoJSON and upper-bound affected area (km^2).
    Note: This is an affected-area upper bound, NOT exact burned area.
    """
    pts = [(obs.longitude, obs.latitude) for obs in observations]
    geom = MultiPoint(pts).convex_hull.buffer(0.005)
    centroid = geom.centroid
    # Approximate degree-to-km scaling at cluster latitude
    lat_km = 111.32
    lon_km = 111.32 * max(0.1, math.cos(math.radians(centroid.y)))
    area_km2 = round(geom.area * lat_km * lon_km, 2)
    return mapping(geom), area_km2
