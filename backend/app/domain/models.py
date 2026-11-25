from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DataOrigin(str, Enum):
    REAL_FIRMS = "REAL_FIRMS"
    SIMULATED_DEMO = "SIMULATED_DEMO"


class IncidentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    MONITORING = "MONITORING"
    CLOSED = "CLOSED"


class PriorityTier(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


@dataclass
class RawObservation:
    """Normalized satellite fire detection prior to persistence."""

    source_sensor: str
    satellite: str
    latitude: float
    longitude: float
    acq_timestamp: datetime
    brightness: float
    frp: float
    confidence_raw: str
    confidence_norm: float
    daynight: str
    data_origin: DataOrigin
    dedup_hash: str
    scan: float | None = None
    track: float | None = None


@dataclass
class PriorityResult:
    """Explainable rule-based priority score (not an ML prediction)."""

    score: float
    tier: PriorityTier
    rules_triggered: list[dict[str, Any]] = field(default_factory=list)
    disclaimer: str = (
        "Rule-based heuristic score for monitoring prioritization; "
        "not an ML prediction or calibrated probability."
    )
