import math
from pathlib import Path
import httpx
import numpy as np

COPERNICUS_GLO30_METADATA = {
    "dataset": "Copernicus DEM GLO-30",
    "version": "2023_1",
    "provider": "ESA / Copernicus (AWS Open Data)",
    "resolution_m": 30.0,
    "vertical_datum": "EGM2008",
    "crs": "EPSG:4326",
    "license": "Free and open (Copernicus)",
}

DEM_CACHE_DIR = Path("data/dem_cache")


def copernicus_tile_id(lat: float, lon: float) -> str:
    """
    Resolve 1x1 degree Copernicus DEM GLO-30 tile identifier for (lat, lon).
    Handles negative coordinates using math.floor().
    """
    lat_f = math.floor(lat)
    lon_f = math.floor(lon)
    ns = "N" if lat_f >= 0 else "S"
    ew = "E" if lon_f >= 0 else "W"
    return f"Copernicus_DSM_COG_10_{ns}{abs(lat_f):02d}_00_{ew}{abs(lon_f):03d}_00_DEM"


def required_tiles_for_radius(lat: float, lon: float, radius_m: float) -> list[str]:
    """Return all 1x1 degree tile IDs intersecting a metric radius around (lat, lon)."""
    dlat = radius_m / 111320.0
    dlon = radius_m / (111320.0 * max(0.1, math.cos(math.radians(lat))))
    lat_min, lat_max = math.floor(lat - dlat), math.floor(lat + dlat)
    lon_min, lon_max = math.floor(lon - dlon), math.floor(lon + dlon)
    tiles = []
    for la in range(lat_min, lat_max + 1):
        for lo in range(lon_min, lon_max + 1):
            tiles.append(copernicus_tile_id(la + 0.5, lo + 0.5))
    return sorted(set(tiles))


def _is_valid_geotiff(path: Path) -> bool:
    """Verify file exists, is non-empty, and starts with TIFF magic bytes."""
    if not path.exists() or path.stat().st_size < 1024:
        return False
    with path.open("rb") as f:
        header = f.read(4)
    return header in (b"II*\x00", b"MM\x00*")


def fetch_copernicus_tile(tile_id: str, cache_dir: Path = DEM_CACHE_DIR, timeout_s: float = 15.0) -> Path | None:
    """
    Download and cache a Copernicus GLO-30 COG tile with integrity validation.
    Returns local Path if valid, or None if unavailable/corrupt.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / f"{tile_id}.tif"
    if _is_valid_geotiff(dest):
        return dest

    url = f"https://copernicus-dem-30m.s3.amazonaws.com/{tile_id}/{tile_id}.tif"
    tmp = cache_dir / f"{tile_id}.tif.part"
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return None
            tmp.write_bytes(resp.content)
        if not _is_valid_geotiff(tmp):
            tmp.unlink(missing_ok=True)
            return None
        tmp.replace(dest)
        return dest
    except Exception:
        tmp.unlink(missing_ok=True)
        return None


def load_dem_patch(
    center_lat: float,
    center_lon: float,
    radius_m: float = 3000.0,
    cell_size_m: float = 30.0,
    strict_real_data: bool = False,
) -> tuple[np.ndarray | None, dict]:
    """
    Return a metric DEM patch (meters) centered on (center_lat, center_lon).
    In strict_real_data mode, returns (None, NO_TERRAIN_AVAILABLE) when real tiles
    are not locally cached/available instead of silently falling back to synthetic data.
    """
    tile_ids = required_tiles_for_radius(center_lat, center_lon, radius_m)

    if strict_real_data:
        return None, {
            **COPERNICUS_GLO30_METADATA,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "cell_size_m": cell_size_m,
            "tile_ids": tile_ids,
            "source_type": "NO_TERRAIN_AVAILABLE",
            "is_synthetic": False,
            "terrain_available": False,
        }

    half_cells = int(radius_m / cell_size_m) + 2
    size = 2 * half_cells + 1
    y_idx, x_idx = np.mgrid[0:size, 0:size]
    dy = (y_idx - half_cells) * cell_size_m
    dx = (x_idx - half_cells) * cell_size_m

    phase = (abs(center_lat) + abs(center_lon)) * 0.1
    base_elev = 450.0 + 180.0 * np.sin(dx / 1200.0 + phase) * np.cos(dy / 1400.0)
    slope_ramp = 0.08 * dy + 0.04 * dx
    dem = base_elev + slope_ramp

    meta = {
        **COPERNICUS_GLO30_METADATA,
        "center_lat": center_lat,
        "center_lon": center_lon,
        "cell_size_m": cell_size_m,
        "tile_ids": tile_ids,
        "source_type": "SYNTHETIC_DEM",
        "is_synthetic": True,
        "terrain_available": True,
    }
    return dem, meta
