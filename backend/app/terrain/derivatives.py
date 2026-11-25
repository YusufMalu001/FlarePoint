import math
import numpy as np


def compute_slope_aspect_horn(
    dem: np.ndarray, cell_size_m: float = 30.0
) -> tuple[np.ndarray, np.ndarray]:
    """
    Horn's (1981) 3x3 finite-difference slope (degrees) and aspect (degrees, 0=N, 90=E).
    Edges and cells adjacent to NaN are returned as NaN.
    """
    z = dem.astype(float)
    slope = np.full_like(z, np.nan)
    aspect = np.full_like(z, np.nan)

    dz_dx = (
        (z[:-2, 2:] + 2.0 * z[1:-1, 2:] + z[2:, 2:])
        - (z[:-2, :-2] + 2.0 * z[1:-1, :-2] + z[2:, :-2])
    ) / (8.0 * cell_size_m)

    dz_dy = (
        (z[2:, :-2] + 2.0 * z[2:, 1:-1] + z[2:, 2:])
        - (z[:-2, :-2] + 2.0 * z[:-2, 1:-1] + z[:-2, 2:])
    ) / (8.0 * cell_size_m)

    grad = np.hypot(dz_dx, dz_dy)
    slope[1:-1, 1:-1] = np.degrees(np.arctan(grad))

    # Geographic downslope azimuth for north-up rasters (x=East, y=South):
    # 0=North, 90=East, 180=South, 270=West
    az = np.degrees(np.arctan2(-dz_dx, dz_dy))
    aspect[1:-1, 1:-1] = np.where(grad > 1e-9, (az + 360.0) % 360.0, np.nan)
    return slope, aspect


def compute_tri(dem: np.ndarray) -> np.ndarray:
    """Terrain Ruggedness Index (Riley et al., 1999): RMS difference to 8 neighbors (m)."""
    z = dem.astype(float)
    tri = np.full_like(z, np.nan)
    c = z[1:-1, 1:-1]
    sq_sum = np.zeros_like(c)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            nbr = z[1 + dy : z.shape[0] - 1 + dy, 1 + dx : z.shape[1] - 1 + dx]
            sq_sum += (nbr - c) ** 2
    tri[1:-1, 1:-1] = np.sqrt(sq_sum / 8.0)
    return tri


def compute_tpi(dem: np.ndarray) -> np.ndarray:
    """Topographic Position Index: center elevation minus 8-neighbor mean (m)."""
    z = dem.astype(float)
    tpi = np.full_like(z, np.nan)
    c = z[1:-1, 1:-1]
    nbr_sum = np.zeros_like(c)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            nbr_sum += z[1 + dy : z.shape[0] - 1 + dy, 1 + dx : z.shape[1] - 1 + dx]
    tpi[1:-1, 1:-1] = c - (nbr_sum / 8.0)
    return tpi


def compute_curvature(dem: np.ndarray, cell_size_m: float = 30.0) -> np.ndarray:
    """Laplacian curvature (1/m): positive = convex/ridge, negative = concave/valley."""
    z = dem.astype(float)
    curv = np.full_like(z, np.nan)
    d2x = (z[1:-1, 2:] - 2.0 * z[1:-1, 1:-1] + z[1:-1, :-2]) / (cell_size_m ** 2)
    d2y = (z[2:, 1:-1] - 2.0 * z[1:-1, 1:-1] + z[:-2, 1:-1]) / (cell_size_m ** 2)
    curv[1:-1, 1:-1] = d2x + d2y
    return curv


def circular_mean_deg(angles_deg: np.ndarray) -> float | None:
    """Circular mean of aspect angles in [0, 360)."""
    valid = angles_deg[~np.isnan(angles_deg)]
    if valid.size == 0:
        return None
    rad = np.radians(valid)
    mean_sin = float(np.mean(np.sin(rad)))
    mean_cos = float(np.mean(np.cos(rad)))
    if math.hypot(mean_sin, mean_cos) < 1e-6:
        return None
    return round((math.degrees(math.atan2(mean_sin, mean_cos)) + 360.0) % 360.0, 2)
