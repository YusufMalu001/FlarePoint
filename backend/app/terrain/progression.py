import math
from typing import Sequence

from app.analytics.clustering import haversine_km
from app.storage.models import IncidentSnapshotModel
from app.terrain.extractor import extract_multiscale_terrain

DISCLAIMER = (
    "Satellite detection centroid displacement is a spatial change in observed detections "
    "and is not a direct estimate of fire-front movement."
)


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def classify_terrain_relative_displacement(
    displacement_km: float,
    bearing_deg: float,
    elev_delta_m: float,
    local_slope_deg: float | None,
    local_aspect_deg: float | None,
) -> str:
    """
    Phase E: Classify observed centroid displacement relative to local terrain gradient.
    """
    if displacement_km < 0.05 or local_slope_deg is None or local_slope_deg < 2.0:
        return "indeterminate"
    if local_aspect_deg is None:
        return "uphill-oriented" if elev_delta_m > 5.0 else ("downhill-oriented" if elev_delta_m < -5.0 else "indeterminate")

    # Uphill direction is opposite to downslope aspect
    uphill_dir = (local_aspect_deg + 180.0) % 360.0
    diff = abs(((bearing_deg - uphill_dir + 180.0) % 360.0) - 180.0)
    if diff <= 45.0:
        return "uphill-oriented"
    if diff >= 135.0:
        return "downhill-oriented"
    return "cross-slope"


def analyze_incident_progression(snapshots: Sequence[IncidentSnapshotModel]) -> dict:
    """Compute Observed Incident Centroid Displacement across consecutive snapshots."""
    transitions = []
    for prev, curr in zip(snapshots, snapshots[1:]):
        dist_km = haversine_km(prev.centroid_lat, prev.centroid_lon, curr.centroid_lat, curr.centroid_lon)
        bearing = _bearing_deg(prev.centroid_lat, prev.centroid_lon, curr.centroid_lat, curr.centroid_lon)
        elapsed_h = max(0.1, (curr.window_start - prev.window_start).total_seconds() / 3600.0)

        t_prev = extract_multiscale_terrain(prev.centroid_lat, prev.centroid_lon, scales_m=(250,))
        t_curr = extract_multiscale_terrain(curr.centroid_lat, curr.centroid_lon, scales_m=(250,))
        elev_delta = round(
            t_curr["center_point"]["elevation_m"] - t_prev["center_point"]["elevation_m"], 1
        )
        cls = classify_terrain_relative_displacement(
            dist_km,
            bearing,
            elev_delta,
            t_prev["center_point"]["slope_deg"],
            t_prev["center_point"]["aspect_deg"],
        )
        quality_flags = ["SYNTHETIC_TERRAIN"]
        if dist_km < 0.05:
            quality_flags.append("MOVEMENT_BELOW_RESOLUTION")
        if elapsed_h > 24.0:
            quality_flags.append("LONG_OBSERVATION_GAP")
        if (t_prev["center_point"]["slope_deg"] or 0.0) < 2.0:
            quality_flags.append("FLAT_TERRAIN")

        transitions.append(
            {
                "from_window": prev.window_start.isoformat(),
                "to_window": curr.window_start.isoformat(),
                "displacement_km": round(dist_km, 3),
                "bearing_deg": round(bearing, 1),
                "elapsed_hours": round(elapsed_h, 1),
                "elevation_delta_m": elev_delta,
                "classification": cls,
                "quality_flags": quality_flags,
            }
        )

    return {
        "label": "Observed Incident Centroid Displacement",
        "disclaimer": DISCLAIMER,
        "transitions": transitions,
    }
