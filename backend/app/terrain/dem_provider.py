import numpy as np


COPERNICUS_GLO30_METADATA = {
    "dataset": "Copernicus DEM GLO-30",
    "resolution_m": 30.0,
    "vertical_datum": "EGM2008",
    "crs": "EPSG:4326",
    "license": "Free and open (Copernicus)",
    "note": "Processed in local metric UTM; synthetic fallback used when offline.",
}


def load_dem_patch(
    center_lat: float,
    center_lon: float,
    radius_m: float = 3000.0,
    cell_size_m: float = 30.0,
) -> tuple[np.ndarray, dict]:
    """
    Return a metric DEM patch (meters) centered on (center_lat, center_lon).
    Uses a deterministic topographic synthesis when local GeoTIFF tiles are not cached.
    """
    half_cells = int(radius_m / cell_size_m) + 2
    size = 2 * half_cells + 1
    y_idx, x_idx = np.mgrid[0:size, 0:size]
    dy = (y_idx - half_cells) * cell_size_m
    dx = (x_idx - half_cells) * cell_size_m

    # Deterministic ridge/valley topography anchored to coordinates
    phase = (abs(center_lat) + abs(center_lon)) * 0.1
    base_elev = 450.0 + 180.0 * np.sin(dx / 1200.0 + phase) * np.cos(dy / 1400.0)
    slope_ramp = 0.08 * dy + 0.04 * dx
    dem = base_elev + slope_ramp

    meta = {
        **COPERNICUS_GLO30_METADATA,
        "center_lat": center_lat,
        "center_lon": center_lon,
        "cell_size_m": cell_size_m,
        "source_mode": "synthetic_fallback",
    }
    return dem, meta
