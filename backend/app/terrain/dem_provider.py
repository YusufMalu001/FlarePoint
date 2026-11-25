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


def local_utm_crs(lat: float, lon: float) -> str:
    """Compute local metric UTM EPSG code from WGS84 (lat, lon)."""
    zone = int((lon + 180.0) / 6.0) + 1
    return f"EPSG:{32600 + zone if lat >= 0 else 32700 + zone}"


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


def fetch_copernicus_tile(tile_id: str, cache_dir: Path = DEM_CACHE_DIR, timeout_s: float = 60.0) -> Path | None:
    """
    Download and cache a Copernicus GLO-30 COG tile with streaming & integrity validation.
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
            with client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    return None
                with tmp.open("wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        f.write(chunk)
        if not _is_valid_geotiff(tmp):
            tmp.unlink(missing_ok=True)
            return None
        tmp.replace(dest)
        return dest
    except Exception:
        tmp.unlink(missing_ok=True)
        return None


def load_real_geotiff_patch(
    tile_paths: list[Path],
    center_lat: float,
    center_lon: float,
    radius_m: float = 3000.0,
    cell_size_m: float = 30.0,
) -> tuple[np.ndarray, dict] | None:
    """
    Load and mosaic real GeoTIFF tile(s) and reproject to local metric UTM CRS
    using bilinear resampling. Returns (dem_array, metadata) or None on failure.
    """
    try:
        import rasterio
        from rasterio.merge import merge
        from rasterio.transform import from_origin
        from rasterio.warp import Resampling, reproject
        from pyproj import Transformer
    except ImportError:
        return None

    datasets = []
    try:
        for p in tile_paths:
            datasets.append(rasterio.open(p))
        if not datasets:
            return None

        dlat = (radius_m + 500.0) / 111320.0
        dlon = (radius_m + 500.0) / (111320.0 * max(0.1, math.cos(math.radians(center_lat))))
        mosaic, src_transform = merge(
            datasets,
            bounds=(center_lon - dlon, center_lat - dlat, center_lon + dlon, center_lat + dlat),
        )
        src_crs = datasets[0].crs
        src_nodata = datasets[0].nodata

        dst_crs = local_utm_crs(center_lat, center_lon)
        transformer = Transformer.from_crs("EPSG:4326", dst_crs, always_xy=True)
        cx_m, cy_m = transformer.transform(center_lon, center_lat)

        half_cells = int(radius_m / cell_size_m) + 2
        size = 2 * half_cells + 1
        dst_transform = from_origin(
            cx_m - half_cells * cell_size_m,
            cy_m + half_cells * cell_size_m,
            cell_size_m,
            cell_size_m,
        )
        dst_arr = np.full((size, size), np.nan, dtype=np.float32)

        reproject(
            source=mosaic[0].astype(np.float32),
            destination=dst_arr,
            src_transform=src_transform,
            src_crs=src_crs,
            src_nodata=src_nodata,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )

        meta = {
            **COPERNICUS_GLO30_METADATA,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "analysis_crs": dst_crs,
            "resampling_method": "bilinear",
            "cell_size_m": cell_size_m,
            "source_type": "REAL_DEM",
            "is_synthetic": False,
            "terrain_available": True,
        }
        return dst_arr.astype(float), meta
    except Exception:
        return None
    finally:
        for ds in datasets:
            ds.close()


def load_dem_patch(
    center_lat: float,
    center_lon: float,
    radius_m: float = 3000.0,
    cell_size_m: float = 30.0,
    strict_real_data: bool = False,
) -> tuple[np.ndarray | None, dict]:
    """
    Return a metric DEM patch (meters) centered on (center_lat, center_lon).
    Attempts real cached/downloaded Copernicus tiles if strict_real_data=True;
    returns (None, NO_TERRAIN_AVAILABLE) if unavailable in strict mode.
    """
    tile_ids = required_tiles_for_radius(center_lat, center_lon, radius_m)
    dst_crs = local_utm_crs(center_lat, center_lon)

    if strict_real_data:
        cached = [p for tid in tile_ids if (p := fetch_copernicus_tile(tid)) is not None]
        if cached:
            real_res = load_real_geotiff_patch(cached, center_lat, center_lon, radius_m, cell_size_m)
            if real_res is not None:
                arr, meta = real_res
                meta["tile_ids"] = tile_ids
                return arr, meta
        return None, {
            **COPERNICUS_GLO30_METADATA,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "analysis_crs": dst_crs,
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
        "analysis_crs": dst_crs,
        "resampling_method": "none_synthetic_grid",
        "cell_size_m": cell_size_m,
        "tile_ids": tile_ids,
        "source_type": "SYNTHETIC_DEM",
        "is_synthetic": True,
        "terrain_available": True,
    }
    return dem, meta
