from datetime import datetime, timedelta, timezone
from typing import Any
import numpy as np
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform as shp_transform


def parse_epoch_ms(ms: int | float | None) -> datetime | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc)


def match_incidents_to_reference(
    fp_incidents: list[dict[str, Any]],
    ref_features: list[dict[str, Any]],
    analysis_crs: str = "EPSG:32610",
    strong_dist_km: float = 5.0,
    probable_dist_km: float = 15.0,
    temporal_buffer_days: int = 3,
) -> dict[str, Any]:
    """
    Many-to-many spatiotemporal matching between FlarePoint incidents and reference fire perimeters.
    Computes centroid distance, point-to-perimeter distance, detections-in-perimeter fraction,
    fragmentation, merging, and event-level Precision / Recall / F1.
    """
    to_utm = Transformer.from_crs("EPSG:4326", analysis_crs, always_xy=True)

    ref_records = []
    for feat in ref_features:
        props = feat.get("properties", {})
        geom_wgs = shape(feat["geometry"])
        geom_utm = shp_transform(to_utm.transform, geom_wgs)
        c_utm = geom_utm.centroid
        disc_dt = parse_epoch_ms(props.get("attr_FireDiscoveryDateTime"))
        end_dt = parse_epoch_ms(props.get("attr_ContainmentDateTime")) or parse_epoch_ms(
            props.get("attr_ControlDateTime")
        )
        ref_records.append(
            {
                "ref_id": props.get("attr_UniqueFireIdentifier") or props.get("poly_IncidentName") or "UNKNOWN",
                "name": props.get("poly_IncidentName") or "Unnamed",
                "acres": float(props.get("poly_GISAcres") or 0.0),
                "start_dt": disc_dt,
                "end_dt": end_dt,
                "geom_utm": geom_utm,
                "centroid_utm": c_utm,
            }
        )

    matches = []
    fp_to_refs: dict[str, list[str]] = {inc["id"]: [] for inc in fp_incidents}
    ref_to_fps: dict[str, list[str]] = {r["ref_id"]: [] for r in ref_records}

    for inc in fp_incidents:
        ix, iy = to_utm.transform(inc["centroid_lon"], inc["centroid_lat"])
        inc_pt = Point(ix, iy)
        inc_start = inc["first_seen_at"]
        inc_end = inc["last_seen_at"]

        best_match = None
        candidates = []

        for ref in ref_records:
            dist_perim_km = inc_pt.distance(ref["geom_utm"]) / 1000.0
            dist_cent_km = inc_pt.distance(ref["centroid_utm"]) / 1000.0
            if dist_perim_km > probable_dist_km:
                continue

            # Temporal compatibility
            temp_ok = True
            if ref["start_dt"] is not None:
                ref_end = ref["end_dt"] or (ref["start_dt"] + timedelta(days=45))
                if inc_end < (ref["start_dt"] - timedelta(days=temporal_buffer_days)) or inc_start > (
                    ref_end + timedelta(days=temporal_buffer_days)
                ):
                    temp_ok = False

            if not temp_ok:
                continue

            tier = "MATCHED" if dist_perim_km <= strong_dist_km else "PROBABLE_MATCH"

            # Fraction of detections inside perimeter
            obs_pts = inc.get("obs_coords", [])
            inside_cnt = 0
            for olat, olon in obs_pts:
                ox, oy = to_utm.transform(olon, olat)
                if ref["geom_utm"].contains(Point(ox, oy)):
                    inside_cnt += 1
            in_perim_frac = round(inside_cnt / len(obs_pts), 4) if obs_pts else None

            cand = {
                "fp_id": inc["id"],
                "ref_id": ref["ref_id"],
                "ref_name": ref["name"],
                "ref_acres": ref["acres"],
                "tier": tier,
                "dist_to_perimeter_km": round(dist_perim_km, 3),
                "dist_to_centroid_km": round(dist_cent_km, 3),
                "detections_inside_perim_frac": in_perim_frac,
            }
            candidates.append(cand)
            fp_to_refs[inc["id"]].append(ref["ref_id"])
            ref_to_fps[ref["ref_id"]].append(inc["id"])

        candidates.sort(key=lambda x: x["dist_to_perimeter_km"])
        if candidates:
            best_match = candidates[0]
            matches.append({**best_match, "candidate_count": len(candidates)})

    matched_fp_ids = {m["fp_id"] for m in matches}
    matched_ref_ids = {rid for rid, fps in ref_to_fps.items() if len(fps) > 0}

    tp = len(matched_fp_ids)
    fp_unmatched = len(fp_incidents) - tp
    fn_unmatched = len(ref_records) - len(matched_ref_ids)

    precision = round(tp / len(fp_incidents), 4) if fp_incidents else 0.0
    recall = round(len(matched_ref_ids) / len(ref_records), 4) if ref_records else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    fragmented_refs = {rid: fps for rid, fps in ref_to_fps.items() if len(fps) > 1}
    merged_fps = {fid: refs for fid, refs in fp_to_refs.items() if len(refs) > 1}

    perim_dists = [m["dist_to_perimeter_km"] for m in matches]
    cent_dists = [m["dist_to_centroid_km"] for m in matches]

    return {
        "matches": matches,
        "unmatched_fp_ids": [i["id"] for i in fp_incidents if i["id"] not in matched_fp_ids],
        "unmatched_ref_ids": [r["ref_id"] for r in ref_records if r["ref_id"] not in matched_ref_ids],
        "event_metrics": {
            "fp_incidents_total": len(fp_incidents),
            "ref_incidents_total": len(ref_records),
            "true_positives_fp": tp,
            "matched_ref_count": len(matched_ref_ids),
            "unmatched_fp_count": fp_unmatched,
            "unmatched_ref_count": fn_unmatched,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
        "spatial_metrics": {
            "median_perim_dist_km": round(float(np.median(perim_dists)), 3) if perim_dists else None,
            "mean_perim_dist_km": round(float(np.mean(perim_dists)), 3) if perim_dists else None,
            "median_centroid_dist_km": round(float(np.median(cent_dists)), 3) if cent_dists else None,
        },
        "fragmentation": {
            "fragmented_ref_count": len(fragmented_refs),
            "details": fragmented_refs,
        },
        "merging": {
            "merged_fp_count": len(merged_fps),
            "details": merged_fps,
        },
    }
