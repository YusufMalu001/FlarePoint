import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import yaml

from app.analytics.clustering import cluster_observations_spatiotemporal
from app.analytics.continuity import associate_incidents_to_events
from experiments.flarepoint_event_validation.scripts.matching import (
    match_incidents_to_reference,
    parse_epoch_ms,
)
from experiments.flarepoint_event_validation.scripts.run_validation import build_obs_models

VAL_DIR = Path(__file__).resolve().parent.parent


def main():
    cfg = yaml.safe_load((VAL_DIR / "validation_config.yaml").read_text())
    raw_firms = json.loads((VAL_DIR / "data" / "firms_aug2024_norcal.json").read_text())
    obs_models = build_obs_models(raw_firms, cfg)

    wfigs_gj = json.loads((VAL_DIR / "data" / "wfigs_2024_norcal.geojson").read_text())
    start_win = datetime.strptime(cfg["temporal"]["start_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_win = datetime.strptime(cfg["temporal"]["end_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

    active_refs = []
    for feat in wfigs_gj["features"]:
        p = feat.get("properties", {})
        acres = float(p.get("poly_GISAcres") or 0.0)
        disc = parse_epoch_ms(p.get("attr_FireDiscoveryDateTime"))
        cont = parse_epoch_ms(p.get("attr_ContainmentDateTime")) or (disc + timedelta(days=45) if disc else None)
        if acres >= 10.0 and disc is not None and disc <= end_win and (cont is None or cont >= start_win):
            active_refs.append(feat)

    # Baseline (Milestone 4)
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
    baseline = match_incidents_to_reference(fp_incidents, active_refs, analysis_crs=cfg["region"]["analysis_crs"])

    # Continuity-grouped events (Milestone 5)
    events = associate_incidents_to_events(fp_incidents, max_link_km=15.0, max_gap_hours=48.0)
    inc_by_id = {i["id"]: i for i in fp_incidents}
    evt_dicts = [
        {
            "id": e.event_id,
            "centroid_lat": e.centroid_lat,
            "centroid_lon": e.centroid_lon,
            "first_seen_at": e.first_seen_at,
            "last_seen_at": e.last_seen_at,
            "hotspot_count": e.total_hotspots,
            "obs_coords": [pt for mid in e.member_incident_ids for pt in inc_by_id[mid]["obs_coords"]],
        }
        for e in events
    ]
    final_eval = match_incidents_to_reference(evt_dicts, active_refs, analysis_crs=cfg["region"]["analysis_crs"])

    rows = [
        {
            "method": "Baseline (DBSCAN 5km / 24h)",
            "incidents": baseline["event_metrics"]["fp_incidents_total"],
            "matched_incidents": baseline["event_metrics"]["true_positives_fp"],
            "precision": baseline["event_metrics"]["precision"],
            "recall": baseline["event_metrics"]["recall"],
            "f1": baseline["event_metrics"]["f1"],
            "fragmented_refs": baseline["fragmentation"]["fragmented_ref_count"],
            "merged_fps": baseline["merging"]["merged_fp_count"],
        },
        {
            "method": "Continuity Events (15km / 48h)",
            "incidents": final_eval["event_metrics"]["fp_incidents_total"],
            "matched_incidents": final_eval["event_metrics"]["true_positives_fp"],
            "precision": final_eval["event_metrics"]["precision"],
            "recall": final_eval["event_metrics"]["recall"],
            "f1": final_eval["event_metrics"]["f1"],
            "fragmented_refs": final_eval["fragmentation"]["fragmented_ref_count"],
            "merged_fps": final_eval["merging"]["merged_fp_count"],
        },
    ]

    with (VAL_DIR / "results" / "continuity_comparison.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    out = {"note": "Development evaluation on Northern California Aug 1-20, 2024", "comparison": rows}
    (VAL_DIR / "results" / "continuity_comparison.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
