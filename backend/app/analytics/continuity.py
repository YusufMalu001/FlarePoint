from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.analytics.clustering import haversine_km


@dataclass
class ContinuityEvent:
    """Underlying wildfire event grouping fragmented FlarePoint incident clusters."""

    event_id: str
    member_incident_ids: list[str]
    centroid_lat: float
    centroid_lon: float
    first_seen_at: datetime
    last_seen_at: datetime
    total_hotspots: int
    association_reasons: list[str] = field(default_factory=list)


def associate_incidents_to_events(
    incidents: list[dict[str, Any]],
    max_link_km: float = 15.0,
    max_gap_hours: float = 48.0,
) -> list[ContinuityEvent]:
    """
    Phase 1: Explainable, fragmentation-aware incident continuity.
    Groups fragmented FlarePoint clusters into underlying ContinuityEvents while
    preserving original incident IDs and enforcing spatial/temporal merge safeguards.
    """
    if not incidents:
        return []

    sorted_incs = sorted(incidents, key=lambda x: x["first_seen_at"])
    events: list[ContinuityEvent] = []

    for inc in sorted_incs:
        best_evt: ContinuityEvent | None = None
        best_dist = max_link_km + 1.0
        best_reason = ""

        for evt in events:
            dist_km = haversine_km(
                inc["centroid_lat"], inc["centroid_lon"], evt.centroid_lat, evt.centroid_lon
            )
            if dist_km > max_link_km:
                continue

            if inc["first_seen_at"] <= evt.last_seen_at and inc["last_seen_at"] >= evt.first_seen_at:
                gap_h = 0.0
            else:
                gap_h = min(
                    abs((inc["first_seen_at"] - evt.last_seen_at).total_seconds()),
                    abs((evt.first_seen_at - inc["last_seen_at"]).total_seconds()),
                ) / 3600.0

            if gap_h > max_gap_hours:
                continue

            if dist_km < best_dist:
                best_dist = dist_km
                best_evt = evt
                best_reason = (
                    f"Associated {inc['id']} -> {evt.event_id}: "
                    f"centroid_dist={dist_km:.2f}km <= {max_link_km}km, gap={gap_h:.1f}h <= {max_gap_hours}h"
                )

        if best_evt is None:
            evt_id = f"EVT-{len(events) + 1:04d}"
            events.append(
                ContinuityEvent(
                    event_id=evt_id,
                    member_incident_ids=[inc["id"]],
                    centroid_lat=inc["centroid_lat"],
                    centroid_lon=inc["centroid_lon"],
                    first_seen_at=inc["first_seen_at"],
                    last_seen_at=inc["last_seen_at"],
                    total_hotspots=inc.get("hotspot_count", 0),
                    association_reasons=[f"Initialized {evt_id} from {inc['id']}"],
                )
            )
        else:
            n_prev = len(best_evt.member_incident_ids)
            best_evt.member_incident_ids.append(inc["id"])
            best_evt.centroid_lat = (best_evt.centroid_lat * n_prev + inc["centroid_lat"]) / (n_prev + 1)
            best_evt.centroid_lon = (best_evt.centroid_lon * n_prev + inc["centroid_lon"]) / (n_prev + 1)
            best_evt.first_seen_at = min(best_evt.first_seen_at, inc["first_seen_at"])
            best_evt.last_seen_at = max(best_evt.last_seen_at, inc["last_seen_at"])
            best_evt.total_hotspots += inc.get("hotspot_count", 0)
            best_evt.association_reasons.append(best_reason)

    return events
