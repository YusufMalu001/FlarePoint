import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pyproj import Transformer
from scipy import stats

STUDY_DIR = Path(__file__).resolve().parent.parent
AUDIT_DIR = STUDY_DIR / "audit"
FIG_DIR = AUDIT_DIR / "figures"


def morans_i(values: np.ndarray, coords_xy: np.ndarray, max_dist_m: float = 25000.0, seed: int = 42, permutations: int = 499) -> dict:
    """Compute Global Moran's I with row-standardized distance-band weights and permutation p-value."""
    n = len(values)
    z = values - np.mean(values)
    denom = float(np.sum(z ** 2))
    if denom == 0.0 or n < 3:
        return {"morans_i": 0.0, "p_perm": 1.0, "n": n}

    # Pairwise Euclidean distance in EPSG:32610
    diff = coords_xy[:, None, :] - coords_xy[None, :, :]
    dist = np.hypot(diff[:, :, 0], diff[:, :, 1])
    W = np.where((dist > 0) & (dist <= max_dist_m), 1.0, 0.0)
    row_sums = W.sum(axis=1, keepdims=True)
    W = np.divide(W, row_sums, out=np.zeros_like(W), where=row_sums > 0)
    S0 = float(W.sum())
    if S0 == 0.0:
        return {"morans_i": 0.0, "p_perm": 1.0, "n": n}

    I_obs = float((n / S0) * (z @ W @ z) / denom)
    rng = np.random.default_rng(seed)
    ge_count = 0
    for _ in range(permutations):
        zp = rng.permutation(z)
        Ip = float((n / S0) * (zp @ W @ zp) / denom)
        if abs(Ip) >= abs(I_obs):
            ge_count += 1
    p_perm = (ge_count + 1) / (permutations + 1)
    return {"morans_i": round(I_obs, 4), "p_perm": round(p_perm, 4), "n": n, "weight_dist_m": max_dist_m}


def main():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    cells = json.loads((STUDY_DIR / "processed" / "grid_cells.json").read_text())
    orig_res = json.loads((STUDY_DIR / "statistical_results" / "results.json").read_text())

    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32610", always_xy=True)
    coords_xy = np.array([to_utm.transform(c["lon"], c["lat"]) for c in cells])
    counts = np.array([c["detection_count"] for c in cells], dtype=float)
    elevs = np.array([c["elevation_m"] for c in cells], dtype=float)

    # Phase 2: Concentration & Pseudoreplication
    nonzero = sorted([int(c["detection_count"]) for c in cells if c["detection_count"] > 0], reverse=True)
    total_det = sum(nonzero)
    top1_share = round(nonzero[0] / total_det, 4) if total_det else 0.0
    top3_share = round(sum(nonzero[:3]) / total_det, 4) if total_det else 0.0

    # Phase 3: Spatial Dependence (Moran's I)
    mi_det = morans_i(counts, coords_xy, max_dist_m=25000.0)
    mi_elev = morans_i(elevs, coords_xy, max_dist_m=25000.0)

    # Phase 4: Terrain Availability by Elevation Band
    elev_order = ["0-250m", "250-500m", "500-750m", "750-1000m", "1000-1500m", "1500-2000m", "2000m+"]
    avail_rows = []
    for ec in elev_order:
        sub = [c for c in cells if c["elev_class"] == ec]
        det_sum = sum(c["detection_count"] for c in sub)
        area_km2 = len(sub) * 225.0  # 15km x 15km
        avail_rows.append({
            "elev_class": ec,
            "cells": len(sub),
            "area_km2": area_km2,
            "detections": det_sum,
            "density_per_100km2": round((det_sum / area_km2) * 100.0, 2) if area_km2 else 0.0,
        })

    # Phase 5-6: Elevation Robustness Analyses
    robustness_rows = []

    # 1. Original H1 (7 classes, n=293)
    h1 = orig_res["tests"]["H1_elevation_kruskal"]
    robustness_rows.append({
        "analysis": "1_original_h1_15km_7classes",
        "unit": "15km_grid_cell",
        "n": h1["n_total"],
        "test": "Kruskal-Wallis",
        "statistic": h1["statistic"],
        "p_value": round(h1["p_value"], 6),
        "effect_size": h1["epsilon_squared"],
    })

    # 2. High/nominal confidence only
    hc = orig_res["sensitivity_high_conf_elevation"]
    robustness_rows.append({
        "analysis": "2_high_nominal_conf_15km",
        "unit": "15km_grid_cell",
        "n": hc["n_total"],
        "test": "Kruskal-Wallis",
        "statistic": hc["statistic"],
        "p_value": round(hc["p_value"], 6),
        "effect_size": hc["epsilon_squared"],
    })

    # 3. Binary presence/absence (Mann-Whitney U on elevation)
    fire_elevs = elevs[counts > 0]
    zero_elevs = elevs[counts == 0]
    u_stat, u_p = stats.mannwhitneyu(fire_elevs, zero_elevs, alternative="two-sided")
    # Rank-biserial correlation
    rb_r = 1.0 - (2.0 * float(u_stat)) / (len(fire_elevs) * len(zero_elevs))
    robustness_rows.append({
        "analysis": "3_presence_absence_mann_whitney",
        "unit": "15km_grid_cell",
        "n": len(cells),
        "test": "Mann-Whitney U",
        "statistic": round(float(u_stat), 2),
        "p_value": round(float(u_p), 6),
        "effect_size": round(abs(rb_r), 4),
    })

    # 4. Coarser 4 elevation bands (<500, 500-1000, 1000-1500, 1500+)
    coarse_groups: dict[str, list[float]] = {}
    for c in cells:
        e = c["elevation_m"]
        grp = "<500m" if e < 500 else ("500-1000m" if e < 1000 else ("1000-1500m" if e < 1500 else "1500m+"))
        coarse_groups.setdefault(grp, []).append(float(c["detection_count"]))
    c_stat, c_p = stats.kruskal(*coarse_groups.values())
    c_eps = max(0.0, (float(c_stat) - 3) / (len(cells) - 4))
    robustness_rows.append({
        "analysis": "4_coarse_4_elev_bands",
        "unit": "15km_grid_cell",
        "n": len(cells),
        "test": "Kruskal-Wallis",
        "statistic": round(float(c_stat), 4),
        "p_value": round(float(c_p), 6),
        "effect_size": round(c_eps, 4),
    })

    # 5. Spatial block aggregation (30km x 30km blocks = 2x2 pooling)
    blocks: dict[tuple[int, int], list[dict]] = {}
    for c in cells:
        _, ix_s, iy_s = c["cell_id"].split("_")
        bx, by = int(ix_s) // 2, int(iy_s) // 2
        blocks.setdefault((bx, by), []).append(c)

    block_groups: dict[str, list[float]] = {}
    for b_cells in blocks.values():
        mean_e = float(np.mean([x["elevation_m"] for x in b_cells]))
        det_sum = float(sum(x["detection_count"] for x in b_cells))
        grp = "<500m" if mean_e < 500 else ("500-1000m" if mean_e < 1000 else ("1000-1500m" if mean_e < 1500 else "1500m+"))
        block_groups.setdefault(grp, []).append(det_sum)
    valid_bg = [v for v in block_groups.values() if len(v) >= 2]
    b_stat, b_p = stats.kruskal(*valid_bg)
    b_eps = max(0.0, (float(b_stat) - (len(valid_bg) - 1)) / max(1, len(blocks) - len(valid_bg)))
    robustness_rows.append({
        "analysis": "5_spatial_blocks_30km",
        "unit": "30km_spatial_block",
        "n": len(blocks),
        "test": "Kruskal-Wallis",
        "statistic": round(float(b_stat), 4),
        "p_value": round(float(b_p), 6),
        "effect_size": round(b_eps, 4),
    })

    # Write CSV
    with (AUDIT_DIR / "elevation_robustness_results.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(robustness_rows[0].keys()))
        writer.writeheader()
        writer.writerows(robustness_rows)

    # Figures
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(range(1, len(nonzero) + 1), nonzero, color="#ef4444", edgecolor="#0f172a")
    ax.set_title(f"Detection Concentration Across {len(nonzero)} Active Grid Cells (Total={total_det})")
    ax.set_xlabel("Active 15 km Grid Cell Rank")
    ax.set_ylabel("VIIRS Detection Count")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "cell_concentration.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([r["elev_class"] for r in avail_rows], [r["cells"] for r in avail_rows], alpha=0.6, label="Total Land Cells (n=293)")
    ax.set_title("Terrain Availability Across Elevation Bands (15 km Grid)")
    ax.set_ylabel("Grid Cell Count")
    ax.tick_params(axis="x", rotation=25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "terrain_availability.png", dpi=150)
    plt.close(fig)

    summary = {
        "concentration": {"active_cells": len(nonzero), "total_cells": len(cells), "top1_share": top1_share, "top3_share": top3_share},
        "morans_i_detections": mi_det,
        "morans_i_elevation": mi_elev,
        "availability": avail_rows,
        "robustness": robustness_rows,
    }
    (AUDIT_DIR / "audit_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
