import numpy as np

from app.terrain.dem_provider import load_dem_patch
from app.terrain.derivatives import (
    circular_mean_deg,
    compute_curvature,
    compute_slope_aspect_horn,
    compute_tpi,
    compute_tri,
)


def extract_multiscale_terrain(
    lat: float,
    lon: float,
    scales_m: tuple[int, ...] = (250, 500, 1000, 3000),
    cell_size_m: float = 30.0,
) -> dict:
    """
    Phase C & D: Extract terrain derivatives and multi-scale neighborhood statistics.
    """
    max_r = max(scales_m) + 120
    dem, meta = load_dem_patch(lat, lon, radius_m=max_r, cell_size_m=cell_size_m)
    slope, aspect = compute_slope_aspect_horn(dem, cell_size_m=cell_size_m)
    tri = compute_tri(dem)
    tpi = compute_tpi(dem)
    curv = compute_curvature(dem, cell_size_m=cell_size_m)

    cy, cx = dem.shape[0] // 2, dem.shape[1] // 2
    y_idx, x_idx = np.ogrid[: dem.shape[0], : dem.shape[1]]
    dist_m = np.hypot((x_idx - cx) * cell_size_m, (y_idx - cy) * cell_size_m)

    scales_out = []
    for r in scales_m:
        mask = dist_m <= r
        e_vals = dem[mask]
        s_vals = slope[mask]
        s_valid = s_vals[~np.isnan(s_vals)]
        t_vals = tri[mask]
        t_valid = t_vals[~np.isnan(t_vals)]
        p_vals = tpi[mask]
        p_valid = p_vals[~np.isnan(p_vals)]

        scales_out.append(
            {
                "scale_m": r,
                "elev_mean_m": round(float(np.nanmean(e_vals)), 1),
                "elev_range_m": round(float(np.nanmax(e_vals) - np.nanmin(e_vals)), 1),
                "slope_mean_deg": round(float(np.mean(s_valid)), 2) if s_valid.size else None,
                "slope_std_deg": round(float(np.std(s_valid)), 2) if s_valid.size else None,
                "aspect_circ_mean_deg": circular_mean_deg(aspect[mask]),
                "tri_mean_m": round(float(np.mean(t_valid)), 2) if t_valid.size else None,
                "tpi_mean_m": round(float(np.mean(p_valid)), 2) if p_valid.size else None,
            }
        )

    return {
        "metadata": meta,
        "center_point": {
            "elevation_m": round(float(dem[cy, cx]), 1),
            "slope_deg": round(float(slope[cy, cx]), 2) if not np.isnan(slope[cy, cx]) else None,
            "aspect_deg": round(float(aspect[cy, cx]), 2) if not np.isnan(aspect[cy, cx]) else None,
            "tri_m": round(float(tri[cy, cx]), 2) if not np.isnan(tri[cy, cx]) else None,
            "tpi_m": round(float(tpi[cy, cx]), 2) if not np.isnan(tpi[cy, cx]) else None,
            "curvature_1_per_m": round(float(curv[cy, cx]), 6) if not np.isnan(curv[cy, cx]) else None,
        },
        "multiscale": scales_out,
    }
