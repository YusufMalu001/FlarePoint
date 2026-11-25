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
    """Canonical normalized satellite fire observation prior to persistence."""

    source_sensor: str
    satellite: str
    instrument: str
    latitude: float
    longitude: float
    acq_date: str
    acq_time: str
    acq_timestamp: datetime
    confidence_raw: str | None
    confidence_norm: float | None
    brightness: float | None
    frp: float | None
    scan: float | None
    track: float | None
    daynight: str | None
    version: str | None
    data_origin: DataOrigin
    dedup_hash: str
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Explicit validation outcome for a single parsed observation record."""

    is_valid: bool
    observation: RawObservation | None = None
    errors: list[str] = field(default_factory=list)


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
