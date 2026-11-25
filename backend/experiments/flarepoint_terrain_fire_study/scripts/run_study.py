import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml
from pyproj import Transformer
from scipy import stats

from app.adapters.firms import FirmsAdapter
from app.analytics.clustering import cluster_observations_spatiotemporal
from app.domain.models import DataOrigin
from app.pipelines.normalize import validate_and_normalize_row
from app.storage.models import ObservationModel
from app.terrain.extractor import extract_multiscale_terrain
from experiments.flarepoint_terrain_fire_study.scripts.study_lib import (
    benjamini_hochberg_fdr,
    classify_aspect_sector,
    classify_elevation,
    classify_slope,
    kruskal_by_group,
)

STUDY_DIR = Path(__file__).resolve().parent.parent


def main():
    cfg = yaml.safe_load((STUDY_DIR / "study_config.yaml").read_text())
    west, south, east, north = cfg["region"]["bbox_wgs84"]
    bbox_str = f"{west},{south},{east},{north}"

    # 1. Collect real NASA FIRMS observations in 5-day chunks
    adapter = FirmsAdapter()
    start_dt = datetime.strptime(cfg["temporal"]["start_date"], "%Y-%m-%d")
    end_dt = datetime.strptime(cfg["temporal"]["end_date"], "%Y-%m-%d")
    chunk_days = int(cfg["temporal"]["chunk_days"])

    seen_hashes: set[str] = set()
    valid_obs = []
    raw_count = 0
    invalid_count = 0

    cur = start_dt
    while cur <= end_dt:
        date_str = cur.strftime("%Y-%m-%d")
        rows = adapter.fetch_area_csv(
            source=cfg["firms"]["source"],
            bbox=bbox_str,
            day_range=chunk_days,
            date=date_str,
        )
        raw_count += len(rows)
        for r in rows:
            res = validate_and_normalize_row(r, cfg["firms"]["source"], DataOrigin.REAL_FIRMS)
            if not res.is_valid or res.observation is None:
                invalid_count += 1
                continue
            o = res.observation
            if not (south <= o.latitude <= north and west <= o.longitude <= east):
                continue
            if o.dedup_hash in seen_hashes:
                continue
            seen_hashes.add(o.dedup_hash)
            valid_obs.append(o)
        cur += timedelta(days=chunk_days)

    # Cluster observations to distinguish unique incidents from raw detections
    obs_models = [
        ObservationModel(
            id=f"obs-{i}",
            ingestion_run_id="study",
            source_sensor=o.source_sensor,
            satellite=o.satellite,
            instrument=o.instrument,
            acq_date=o.acq_date,
            acq_time=o.acq_time,
            acq_timestamp=o.acq_timestamp,
            latitude=o.latitude,
            longitude=o.longitude,
            brightness=o.brightness,
            frp=o.frp,
            confidence_raw=o.confidence_raw,
            confidence_norm=o.confidence_norm,
            daynight=o.daynight,
            raw_payload={},
            dedup_hash=o.dedup_hash,
            data_origin=o.data_origin.value,
        )
        for i, o in enumerate(valid_obs)
    ]
    clustering = cluster_observations_spatiotemporal(obs_models)

    # 2. Build 10km x 10km background grid in EPSG:32610 (including zero-detection cells)
    to_utm = Transformer.from_crs("EPSG:4326", cfg["region"]["analysis_crs"], always_xy=True)
    to_wgs = Transformer.from_crs(cfg["region"]["analysis_crs"], "EPSG:4326", always_xy=True)

    x_min, y_min = to_utm.transform(west, south)
    x_max, y_max = to_utm.transform(east, north)
    cell_m = float(cfg["grid"]["cell_size_m"])

    # Assign observations to grid cell indices
    cell_obs: dict[tuple[int, int], list] = {}
    for o in valid_obs:
        ox, oy = to_utm.transform(o.longitude, o.latitude)
        ix = int((ox - x_min) // cell_m)
        iy = int((oy - y_min) // cell_m)
        cell_obs.setdefault((ix, iy), []).append(o)

    nx = int((x_max - x_min) // cell_m)
    ny = int((y_max - y_min) // cell_m)

    grid_cells = []
    for ix in range(nx):
        for iy in range(ny):
            cx_m = x_min + (ix + 0.5) * cell_m
            cy_m = y_min + (iy + 0.5) * cell_m
            clon, clat = to_wgs.transform(cx_m, cy_m)
            if not (south <= clat <= north and west <= clon <= east):
                continue
            ter = extract_multiscale_terrain(
                clat, clat and clat or clat,  # replaced below
                scales_m=tuple(cfg["terrain"]["scales_m"]),
                strict_real_data=True,
            ) if False else extract_multiscale_terrain(
                clat, clon, scales_m=tuple(cfg["terrain"]["scales_m"]), strict_real_data=True
            )
            cp = ter["center_point"]
            if cp is None or cp["elevation_m"] is None or np.isnan(cp["elevation_m"]) or cp["elevation_m"] <= 0:
                continue

            obs_in_cell = cell_obs.get((ix, iy), [])
            ms_250 = next((m for m in ter["multiscale"] if m["scale_m"] == 250), {})
            ms_3000 = next((m for m in ter["multiscale"] if m["scale_m"] == 3000), {})

            elev_cls = classify_elevation(cp["elevation_m"], cfg["bins"]["elevation_m"])
            slope_cls = classify_slope(cp["slope_deg"], cfg["bins"]["slope_deg"])
            aspect_sec = classify_aspect_sector(
                cp["aspect_deg"], cp["slope_deg"], cfg["terrain"]["flat_slope_threshold_deg"]
            )
            grid_cells.append(
                {
                    "cell_id": f"G_{ix}_{iy}",
                    "lat": round(clat, 5),
                    "lon": round(clon, 5),
                    "detection_count": len(obs_in_cell),
                    "high_conf_count": sum(1 for o in obs_in_cell if o.confidence_raw in ("h", "n")),
                    "elevation_m": cp["elevation_m"],
                    "slope_deg": cp["slope_deg"],
                    "aspect_deg": cp["aspect_deg"],
                    "tri_m": cp["tri_m"],
                    "tpi_m": cp["tpi_m"],
                    "curvature": cp["curvature_1_per_m"],
                    "slope_3000m_deg": ms_3000.get("slope_mean_deg"),
                    "tri_3000m_m": ms_3000.get("tri_mean_m"),
                    "elev_class": elev_cls,
                    "slope_class": slope_cls,
                    "aspect_sector": aspect_sec,
                    "terrain_source": ter["metadata"]["source_type"],
                }
            )

    # 3. Statistical tests + Benjamini-Hochberg FDR
    counts = [c["detection_count"] for c in grid_cells]
    kw_elev = kruskal_by_group(counts, [c["elev_class"] for c in grid_cells])
    kw_slope = kruskal_by_group(counts, [c["slope_class"] for c in grid_cells])
    sloped_cells = [c for c in grid_cells if c["aspect_sector"] != "FLAT_UNDEFINED"]
    kw_aspect = kruskal_by_group(
        [c["detection_count"] for c in sloped_cells],
        [c["aspect_sector"] for c in sloped_cells],
    )

    tri_vals = [c["tri_m"] for c in grid_cells if c["tri_m"] is not None]
    tri_cnts = [c["detection_count"] for c in grid_cells if c["tri_m"] is not None]
    sp_tri_stat, sp_tri_p = stats.spearmanr(tri_vals, tri_cnts)

    tri_3k_vals = [c["tri_3000m_m"] for c in grid_cells if c["tri_3000m_m"] is not None]
    tri_3k_cnts = [c["detection_count"] for c in grid_cells if c["tri_3000m_m"] is not None]
    sp_3k_stat, sp_3k_p = stats.spearmanr(tri_3k_vals, tri_3k_cnts)

    # Sensitivity: high/nominal confidence only
    kw_elev_hc = kruskal_by_group([c["high_conf_count"] for c in grid_cells], [c["elev_class"] for c in grid_cells])

    raw_pvals = [
        p for p in [kw_elev["p_value"], kw_slope["p_value"], kw_aspect["p_value"], float(sp_tri_p), float(sp_3k_p)]
        if p is not None
    ]
    adj_pvals = benjamini_hochberg_fdr(raw_pvals)

    results = {
        "study_window": f"{cfg['temporal']['start_date']} to {cfg['temporal']['end_date']}",
        "total_grid_cells": len(grid_cells),
        "cells_with_detections": sum(1 for c in grid_cells if c["detection_count"] > 0),
        "total_detections": len(valid_obs),
        "unique_incidents": len(clustering.clusters),
        "tests": {
            "H1_elevation_kruskal": kw_elev,
            "H2_slope_kruskal": kw_slope,
            "H3_aspect_kruskal_sloped_only": kw_aspect,
            "H4_tri_spearman": {"rho": round(float(sp_tri_stat), 4), "p_value": float(sp_tri_p)},
            "H5_tri_3000m_spearman": {"rho": round(float(sp_3k_stat), 4), "p_value": float(sp_3k_p)},
        },
        "fdr_adjusted_p_values": adj_pvals,
        "sensitivity_high_conf_elevation": kw_elev_hc,
    }

    # Save artifacts
    for sub in ("processed", "statistical_results", "figures", "reports"):
        (STUDY_DIR / sub).mkdir(parents=True, exist_ok=True)

    manifest = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "firms_source": cfg["firms"]["source"],
        "dem_source": cfg["terrain"]["dataset"],
        "raw_fetched": raw_count,
        "invalid_records": invalid_count,
        "deduplicated_in_bbox": len(valid_obs),
        "unique_incidents": len(clustering.clusters),
        "grid_cells_valid_land": len(grid_cells),
        "random_seed": cfg["random_seed"],
    }
    (STUDY_DIR / "data_manifest.json").write_text(json.dumps(manifest, indent=2))
    (STUDY_DIR / "processed" / "grid_cells.json").write_text(json.dumps(grid_cells, indent=2))
    (STUDY_DIR / "statistical_results" / "results.json").write_text(json.dumps(results, indent=2))

    # 4. Generate publication figures
    fig, ax = plt.subplots(figsize=(7, 5))
    sc = ax.scatter(
        [c["lon"] for c in grid_cells],
        [c["lat"] for c in grid_cells],
        c=[c["elevation_m"] for c in grid_cells],
        cmap="terrain",
        s=38,
        marker="s",
    )
    ax.scatter(
        [o.longitude for o in valid_obs],
        [o.latitude for o in valid_obs],
        c="red",
        s=4,
        alpha=0.6,
        label=f"VIIRS Detections (n={len(valid_obs)})",
    )
    plt.colorbar(sc, ax=ax, label="Elevation (m, Copernicus GLO-30)")
    ax.set_title("Northern California Study Area (EPSG:4326) — Real DEM & VIIRS")
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(STUDY_DIR / "figures" / "study_area_detections.png", dpi=150)
    plt.close(fig)

    # Elevation class comparison plot
    elev_order = ["0-250m", "250-500m", "500-750m", "750-1000m", "1000-1500m", "1500-2000m", "2000m+"]
    elev_means = []
    for ec in elev_order:
        vals = [c["detection_count"] for c in grid_cells if c["elev_class"] == ec]
        elev_means.append(np.mean(vals) if vals else 0.0)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(elev_order, elev_means, color="#2dd4bf", edgecolor="#0f172a")
    ax.set_title("Mean VIIRS Detections per 10 km Cell by Elevation Class")
    ax.set_ylabel("Mean Detections / 100 km² Cell")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(STUDY_DIR / "figures" / "elevation_class_comparison.png", dpi=150)
    plt.close(fig)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
