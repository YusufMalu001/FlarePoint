import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from app.analytics.clustering import cluster_observations_spatiotemporal
from app.terrain.dem_provider import load_dem_patch
from app.terrain.derivatives import compute_slope_aspect_horn, compute_tri
from experiments.flarepoint_event_validation.scripts.run_validation import build_obs_models

ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = ROOT / "docs" / "images" / "research"
STUDY_DIR = ROOT / "backend" / "experiments" / "flarepoint_terrain_fire_study"
VAL_DIR = ROOT / "backend" / "experiments" / "flarepoint_event_validation"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 11, "axes.labelsize": 9})

    raw_firms = json.loads((VAL_DIR / "data" / "firms_aug2024_norcal.json").read_text())
    import yaml
    cfg = yaml.safe_load((VAL_DIR / "validation_config.yaml").read_text())
    obs = build_obs_models(raw_firms, cfg)
    wfigs = json.loads((VAL_DIR / "data" / "wfigs_2024_norcal.geojson").read_text())
    grid_cells = json.loads((STUDY_DIR / "processed" / "grid_cells.json").read_text())
    val_summary = json.loads((VAL_DIR / "results" / "validation_summary.json").read_text())

    # 1. Study area & FIRMS detections + WFIGS perimeters
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    for feat in wfigs["features"]:
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            rings = [geom["coordinates"][0]]
        elif geom["type"] == "MultiPolygon":
            rings = [p[0] for p in geom["coordinates"]]
        else:
            rings = []
        for r in rings:
            xs, ys = zip(*r)
            ax.plot(xs, ys, color="#2dd4bf", lw=1.0, alpha=0.8)
    ax.scatter([o.longitude for o in obs], [o.latitude for o in obs], s=3, c="#ef4444", alpha=0.55, label=f"VIIRS_SNPP_SP (n={len(obs)})")
    ax.plot([], [], color="#2dd4bf", lw=1.2, label="NIFC WFIGS 2024 Perimeters")
    ax.set_title("Northern California Study Area — NASA FIRMS & WFIGS (Aug 1–20, 2024)")
    ax.set_xlabel("Longitude (°E, EPSG:4326)")
    ax.set_ylabel("Latitude (°N, EPSG:4326)")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "study_area_detections.png", dpi=300)
    plt.close(fig)

    # 2-5. Real Copernicus DEM GLO-30 Terrain Maps around Boise Fire (41.24632, -123.46512)
    dem, meta = load_dem_patch(41.24632, -123.46512, radius_m=4500.0, cell_size_m=30.0, strict_real_data=True)
    if dem is not None:
        slope, aspect = compute_slope_aspect_horn(dem, cell_size_m=30.0)
        tri = compute_tri(dem)

        for name, arr, cmap, title, unit in [
            ("terrain_elevation.png", dem, "terrain", "Copernicus DEM GLO-30 Elevation (EPSG:32610, Boise Fire Area)", "Elevation (m)"),
            ("terrain_slope.png", slope, "inferno", "Horn 3×3 Slope (EPSG:32610, 30 m)", "Slope (°)"),
            ("terrain_aspect.png", aspect, "twilight", "Downslope Aspect (EPSG:32610, Flat=NaN)", "Aspect (° from N)"),
            ("terrain_tri.png", tri, "viridis", "Terrain Ruggedness Index — TRI (EPSG:32610)", "TRI (m)"),
        ]:
            fig, ax = plt.subplots(figsize=(6.5, 5))
            im = ax.imshow(arr, cmap=cmap, origin="upper")
            plt.colorbar(im, ax=ax, label=unit)
            ax.set_title(title)
            ax.set_xlabel("East–West Grid Index (30 m/px)")
            ax.set_ylabel("North–South Grid Index (30 m/px)")
            fig.tight_layout()
            fig.savefig(OUT_DIR / name, dpi=300)
            plt.close(fig)

    # 6. Elevation availability vs detections
    elev_order = ["0-250m", "250-500m", "500-750m", "750-1000m", "1000-1500m", "1500-2000m", "2000m+"]
    cell_cnts = [sum(1 for c in grid_cells if c["elev_class"] == e) for e in elev_order]
    det_cnts = [sum(c["detection_count"] for c in grid_cells if c["elev_class"] == e) for e in elev_order]
    fig, ax1 = plt.subplots(figsize=(7.5, 4.2))
    x = np.arange(len(elev_order))
    ax1.bar(x - 0.18, cell_cnts, width=0.36, color="#64748b", label="Total Land Cells (n=293)")
    ax1.set_ylabel("15 km Land Cells")
    ax2 = ax1.twinx()
    ax2.bar(x + 0.18, det_cnts, width=0.36, color="#ef4444", label="VIIRS Detections (n=3,294)")
    ax2.set_ylabel("VIIRS Detection Count")
    ax1.set_xticks(x)
    ax1.set_xticklabels(elev_order, rotation=25)
    ax1.set_title("Terrain Availability vs. Satellite Detection Distribution")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "elevation_distribution.png", dpi=300)
    plt.close(fig)

    # 7. Elevation robustness
    with (STUDY_DIR / "audit" / "elevation_robustness_results.csv").open() as f:
        rob = list(csv.DictReader(f))
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    labels = ["Orig 7-Class", "High Conf", "Pres/Abs", "4-Band", "30km Block"]
    pvals = [float(r["p_value"]) for r in rob]
    ax.barh(labels, pvals, color=["#2dd4bf" if p < 0.05 else "#94a3b8" for p in pvals])
    ax.axvline(0.05, color="#ef4444", ls="--", lw=1.2, label="α = 0.05")
    ax.set_xlabel("Raw p-value (Kruskal-Wallis / Mann-Whitney U)")
    ax.set_title("Statistical Robustness Audit: Elevation Association Sensitivity")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "elevation_robustness.png", dpi=300)
    plt.close(fig)

    # 8. Event validation metrics
    em = val_summary["event_metrics"]
    fig, ax = plt.subplots(figsize=(6.5, 4))
    metrics = ["Precision\n(8/11)", "Recall\n(2/4)", "F1\n(Score)"]
    vals = [em["precision"], em["recall"], em["f1"]]
    ax.bar(metrics, vals, color=["#2dd4bf", "#38bdf8", "#f59e0b"], width=0.5)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Score")
    ax.set_title("Milestone 4 Event Validation vs. NIFC WFIGS (Aug 1–20, 2024)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "event_validation.png", dpi=300)
    plt.close(fig)

    # 9. Fragmentation visualization (Park Fire & Boise Fire)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    frag = val_summary["fragmentation"]["details"]
    names = ["Park Fire\n(2024-CABTU-013761)", "Boise Fire\n(2024-CASRF-000729)"]
    counts = [len(frag.get("2024-CABTU-013761", [])), len(frag.get("2024-CASRF-000729", []))]
    ax.bar(names, counts, color=["#ef4444", "#f59e0b"], width=0.45)
    ax.set_ylabel("FlarePoint Cluster Fragments (eps=5 km, 24h)")
    ax.set_title("Incident Fragmentation of Documented WFIGS Wildfires")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "incident_fragmentation.png", dpi=300)
    plt.close(fig)

    # 10. Incident temporal activity (real VIIRS daily detections)
    dates = sorted({o.acq_date for o in obs})
    daily_cnts = [sum(1 for o in obs if o.acq_date == d) for d in dates]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, daily_cnts, marker="o", color="#ef4444", lw=1.5)
    ax.fill_between(dates, daily_cnts, color="#ef4444", alpha=0.15)
    ax.set_title("Daily NASA FIRMS VIIRS_SNPP_SP Detections (Northern California, Aug 2024)")
    ax.set_ylabel("Detection Count")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "incident_timeline.png", dpi=300)
    plt.close(fig)

    print("Generated 10 figures in", OUT_DIR)


if __name__ == "__main__":
    main()
