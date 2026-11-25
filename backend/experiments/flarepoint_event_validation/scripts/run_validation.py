import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

from app.adapters.firms import FirmsAdapter
from app.analytics.clustering import cluster_observations_spatiotemporal
from app.domain.models import DataOrigin
from app.pipelines.normalize import validate_and_normalize_row
from app.storage.models import ObservationModel
from experiments.flarepoint_event_validation.scripts.matching import (
    match_incidents_to_reference,
    parse_epoch_ms,
)

VAL_DIR = Path(__file__).resolve().parent.parent


def load_or_fetch_firms(cfg: dict) -> list[dict]:
    cache_path = VAL_DIR / "data" / "firms_aug2024_norcal.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    west, south, east, north = cfg["region"]["bbox_wgs84"]
    bbox_str = f"{west},{south},{east},{north}"
    adapter = FirmsAdapter()
    start_dt = datetime.strptime(cfg["temporal"]["start_date"], "%Y-%m-%d")
    end_dt = datetime.strptime(cfg["temporal"]["end_date"], "%Y-%m-%d")
    chunk_days = int(cfg["temporal"]["chunk_days"])

    all_rows = []
    cur = start_dt
    while cur <= end_dt:
        rows = adapter.fetch_area_csv(
            source=cfg["firms"]["source"],
            bbox=bbox_str,
            day_range=chunk_days,
            date=cur.strftime("%Y-%m-%d"),
        )
        all_rows.extend(rows)
        cur += timedelta(days=chunk_days)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(all_rows))
    return all_rows


def build_obs_models(raw_rows: list[dict], cfg: dict) -> list[ObservationModel]:
    west, south, east, north = cfg["region"]["bbox_wgs84"]
    seen = set()
    models = []
    for i, r in enumerate(raw_rows):
        res = validate_and_normalize_row(r, cfg["firms"]["source"], DataOrigin.REAL_FIRMS)
        if not res.is_valid or res.observation is None:
            continue
        o = res.observation
        if not (south <= o.latitude <= north and west <= o.longitude <= east):
            continue
        if o.dedup_hash in seen:
            continue
        seen.add(o.dedup_hash)
        models.append(
            ObservationModel(
                id=f"val-{i}",
                ingestion_run_id="val",
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
        )
    return models


def main():
    cfg = yaml.safe_load((VAL_DIR / "validation_config.yaml").read_text())
    raw_firms = load_or_fetch_firms(cfg)
    obs_models = build_obs_models(raw_firms, cfg)

    wfigs_gj = json.loads((VAL_DIR / "data" / "wfigs_2024_norcal.geojson").read_text())
    start_win = datetime.strptime(cfg["temporal"]["start_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_win = datetime.strptime(cfg["temporal"]["end_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

    # Filter reference fires to those active during or overlapping the study window (with >= 10 acres reporting threshold)
    active_refs = []
    for feat in wfigs_gj["features"]:
        p = feat.get("properties", {})
        acres = float(p.get("poly_GISAcres") or 0.0)
        disc = parse_epoch_ms(p.get("attr_FireDiscoveryDateTime"))
        cont = parse_epoch_ms(p.get("attr_ContainmentDateTime")) or (disc + timedelta(days=45) if disc else None)
        if acres < 10.0 or disc is None:
            continue
        if disc <= end_win and (cont is None or cont >= start_win):
            active_refs.append(feat)

    # Primary run (default eps=5.0 km, temporal_gap=24.0 h)
    cl_res = cluster_observations_spatiotemporal(obs_models, eps_km=5.0, min_samples=3, max_temporal_gap_hours=24.0)
    fp_incidents = [
        {
            "id": c.cluster_id,
            "centroid_lat": c.centroid_lat,
            "centroid_lon": c.centroid_lon,
            "first_seen_at": c.first_seen_at,
            "last_seen_at": c.last_seen_at,
            "hotspot_count": c.observation_count,
            "obs_coords": [(o.latitude, o.longitude) for o in c.observations],
        }
        for c in cl_res.clusters
    ]

    eval_out = match_incidents_to_reference(
        fp_incidents,
        active_refs,
        analysis_crs=cfg["region"]["analysis_crs"],
        strong_dist_km=cfg["matching"]["strong_perimeter_dist_km"],
        probable_dist_km=cfg["matching"]["probable_perimeter_dist_km"],
        temporal_buffer_days=cfg["matching"]["temporal_buffer_days"],
    )

    # Sensitivity grid
    sens_rows = []
    for eps_km in cfg["sensitivity"]["eps_km_values"]:
        for gap_h in cfg["sensitivity"]["temporal_gap_hours_values"]:
            sc = cluster_observations_spatiotemporal(
                obs_models, eps_km=eps_km, min_samples=3, max_temporal_gap_hours=gap_h
            )
            s_incs = [
                {
                    "id": c.cluster_id,
                    "centroid_lat": c.centroid_lat,
                    "centroid_lon": c.centroid_lon,
                    "first_seen_at": c.first_seen_at,
                    "last_seen_at": c.last_seen_at,
                    "hotspot_count": c.observation_count,
                    "obs_coords": [(o.latitude, o.longitude) for o in c.observations],
                }
                for c in sc.clusters
            ]
            m = match_incidents_to_reference(s_incs, active_refs, analysis_crs=cfg["region"]["analysis_crs"])
            sens_rows.append(
                {
                    "eps_km": eps_km,
                    "temporal_gap_h": gap_h,
                    "fp_incidents": m["event_metrics"]["fp_incidents_total"],
                    "precision": m["event_metrics"]["precision"],
                    "recall": m["event_metrics"]["recall"],
                    "f1": m["event_metrics"]["f1"],
                    "fragmented_refs": m["fragmentation"]["fragmented_ref_count"],
                    "merged_fps": m["merging"]["merged_fp_count"],
                    "median_perim_dist_km": m["spatial_metrics"]["median_perim_dist_km"],
                }
            )

    for sub in ("results", "figures", "reports"):
        (VAL_DIR / sub).mkdir(parents=True, exist_ok=True)

    (VAL_DIR / "results" / "validation_summary.json").write_text(json.dumps(eval_out, indent=2, default=str))
    with (VAL_DIR / "results" / "sensitivity_results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sens_rows[0].keys()))
        w.writeheader()
        w.writerows(sens_rows)

    # Figures
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot([r["eps_km"] for r in sens_rows if r["temporal_gap_h"] == 24.0],
            [r["f1"] for r in sens_rows if r["temporal_gap_h"] == 24.0], marker="o", label="F1 (gap=24h)")
    ax.plot([r["eps_km"] for r in sens_rows if r["temporal_gap_h"] == 24.0],
            [r["precision"] for r in sens_rows if r["temporal_gap_h"] == 24.0], marker="s", label="Precision")
    ax.plot([r["eps_km"] for r in sens_rows if r["temporal_gap_h"] == 24.0],
            [r["recall"] for r in sens_rows if r["temporal_gap_h"] == 24.0], marker="^", label="Recall")
    ax.set_title("FlarePoint Event Validation — DBSCAN Epsilon Sensitivity (24h Gap)")
    ax.set_xlabel("DBSCAN Epsilon (km)")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.05)
    ax.legend()
    fig.tight_layout()
    fig.savefig(VAL_DIR / "figures" / "threshold_sensitivity.png", dpi=150)
    plt.close(fig)

    print(json.dumps({"event_metrics": eval_out["event_metrics"], "spatial_metrics": eval_out["spatial_metrics"], "fragmentation": eval_out["fragmentation"], "merging": eval_out["merging"]}, indent=2))


if __name__ == "__main__":
    main()
