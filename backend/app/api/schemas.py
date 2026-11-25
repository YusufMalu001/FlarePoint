from datetime import datetime
from typing import Any
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    mode: str
    incident_count: int
    observation_count: int


class IngestRequest(BaseModel):
    source: str | None = None
    bbox: str | None = None
    day_range: int = 3
    force_demo: bool | None = None


class IngestResponse(BaseModel):
    run_id: str
    status: str
    data_origin: str
    records_fetched: int
    records_inserted: int
    incidents_active: int


class IncidentSummary(BaseModel):
    id: str
    persistent_key: str
    first_seen_at: datetime
    last_seen_at: datetime
    status: str
    centroid_lat: float
    centroid_lon: float
    footprint_geojson: dict[str, Any]
    affected_area_km2: float
    hotspot_count: int
    max_frp: float
    mean_frp: float
    cluster_confidence: float
    priority_score: float
    priority_tier: str
    priority_explanation: dict[str, Any]
    weather_context: dict[str, Any]
    land_cover_summary: dict[str, float]
    data_origin: str

    model_config = {"from_attributes": True}


class ObservationOut(BaseModel):
    id: str
    source_sensor: str
    satellite: str
    acq_timestamp: datetime
    latitude: float
    longitude: float
    brightness: float
    frp: float
    confidence_raw: str
    confidence_norm: float
    daynight: str
    data_origin: str

    model_config = {"from_attributes": True}


class SnapshotOut(BaseModel):
    window_start: datetime
    window_end: datetime
    hotspot_count: int
    max_frp: float
    mean_frp: float
    affected_area_km2: float
    centroid_lat: float
    centroid_lon: float

    model_config = {"from_attributes": True}
