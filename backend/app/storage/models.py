import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IngestionRunModel(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    area_bbox: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="RUNNING")
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    data_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ObservationModel(Base):
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ingestion_run_id: Mapped[str] = mapped_column(ForeignKey("ingestion_runs.id"), nullable=False)
    source_sensor: Mapped[str] = mapped_column(String(64), nullable=False)
    satellite: Mapped[str] = mapped_column(String(32), nullable=False)
    acq_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    brightness: Mapped[float] = mapped_column(Float, nullable=False)
    frp: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_raw: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence_norm: Mapped[float] = mapped_column(Float, nullable=False)
    daynight: Mapped[str] = mapped_column(String(4), nullable=False)
    dedup_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    data_origin: Mapped[str] = mapped_column(String(32), nullable=False)


class IncidentModel(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    persistent_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    centroid_lat: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lon: Mapped[float] = mapped_column(Float, nullable=False)
    footprint_geojson: Mapped[dict] = mapped_column(JSON, nullable=False)
    affected_area_km2: Mapped[float] = mapped_column(Float, nullable=False)
    hotspot_count: Mapped[int] = mapped_column(Integer, default=0)
    max_frp: Mapped[float] = mapped_column(Float, default=0.0)
    mean_frp: Mapped[float] = mapped_column(Float, default=0.0)
    cluster_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    priority_tier: Mapped[str] = mapped_column(String(32), default="LOW")
    priority_explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    weather_context: Mapped[dict] = mapped_column(JSON, default=dict)
    land_cover_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    data_origin: Mapped[str] = mapped_column(String(32), nullable=False)

    snapshots: Mapped[list["IncidentSnapshotModel"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )


class IncidentObservationModel(Base):
    __tablename__ = "incident_observations"

    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), primary_key=True)
    observation_id: Mapped[str] = mapped_column(ForeignKey("observations.id"), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IncidentSnapshotModel(Base):
    __tablename__ = "incident_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hotspot_count: Mapped[int] = mapped_column(Integer, nullable=False)
    max_frp: Mapped[float] = mapped_column(Float, nullable=False)
    mean_frp: Mapped[float] = mapped_column(Float, nullable=False)
    affected_area_km2: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lat: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lon: Mapped[float] = mapped_column(Float, nullable=False)

    incident: Mapped["IncidentModel"] = relationship(back_populates="snapshots")


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
