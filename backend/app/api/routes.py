from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analytics.tracking import process_incidents
from app.api.schemas import (
    HealthResponse,
    IncidentSummary,
    IngestRequest,
    IngestResponse,
    IngestionStatusOut,
    ObservationOut,
    PaginatedObservations,
    SnapshotOut,
)
from app.core.config import settings
from app.pipelines.ingest import run_ingestion
from app.terrain.dem_provider import COPERNICUS_GLO30_METADATA
from app.terrain.extractor import extract_multiscale_terrain
from app.terrain.progression import analyze_incident_progression
from app.storage.database import get_db
from app.storage.models import (
    AuditLogModel,
    IncidentModel,
    IncidentObservationModel,
    IncidentSnapshotModel,
    IngestionRunModel,
    ObservationModel,
)

router = APIRouter(prefix="/api/v1")


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    mode = "SIMULATED_DEMO" if (settings.demo_mode or not settings.nasa_firms_map_key) else "REAL_FIRMS"
    return HealthResponse(
        status="ok",
        mode=mode,
        incident_count=db.query(IncidentModel).count(),
        observation_count=db.query(ObservationModel).count(),
    )


@router.get("/sources")
def list_sources():
    """Data-source metadata and NASA FIRMS access documentation."""
    return {
        "active_mode": "SIMULATED_DEMO"
        if (settings.demo_mode or not settings.nasa_firms_map_key)
        else "REAL_FIRMS",
        "sources": [
            {
                "id": "VIIRS_SNPP_NRT",
                "instrument": "VIIRS",
                "satellite": "Suomi-NPP",
                "format": "CSV",
                "rate_limit": "5000 transactions / 10 min per MAP_KEY",
            },
            {
                "id": "VIIRS_NOAA20_NRT",
                "instrument": "VIIRS",
                "satellite": "NOAA-20",
                "format": "CSV",
                "rate_limit": "5000 transactions / 10 min per MAP_KEY",
            },
            {
                "id": "MODIS_NRT",
                "instrument": "MODIS",
                "satellite": "Terra & Aqua",
                "format": "CSV",
                "rate_limit": "5000 transactions / 10 min per MAP_KEY",
            },
        ],
    }


@router.post("/ingest/run", response_model=IngestResponse)
def trigger_ingest(req: IngestRequest, db: Session = Depends(get_db)):
    if not (1 <= req.day_range <= 5):
        raise HTTPException(status_code=422, detail="day_range must be between 1 and 5")
    run = run_ingestion(
        db,
        source=req.source,
        bbox=req.bbox,
        day_range=req.day_range,
        force_demo=req.force_demo,
    )
    incidents = process_incidents(db)
    return IngestResponse(
        run_id=run.id,
        status=run.status,
        data_origin=run.data_origin,
        records_fetched=run.records_fetched,
        records_valid=run.records_valid,
        records_invalid=run.records_invalid,
        records_duplicate=run.records_duplicate,
        records_inserted=run.records_inserted,
        incidents_active=len(incidents),
    )


@router.get("/ingest/status", response_model=list[IngestionStatusOut])
def ingestion_status(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    return (
        db.query(IngestionRunModel)
        .order_by(IngestionRunModel.started_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/observations", response_model=PaginatedObservations)
def list_observations(
    bbox: str | None = Query(None, description="west,south,east,north"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    data_origin: str | None = Query(None, pattern="^(REAL_FIRMS|SIMULATED_DEMO)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(ObservationModel)
    if bbox:
        try:
            w, s, e, n = [float(x) for x in bbox.split(",")]
            if w > e or s > n:
                raise ValueError("Invalid bbox ordering")
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid bbox format; expected west,south,east,north")
        q = q.filter(
            ObservationModel.longitude >= w,
            ObservationModel.longitude <= e,
            ObservationModel.latitude >= s,
            ObservationModel.latitude <= n,
        )
    if start_time:
        q = q.filter(ObservationModel.acq_timestamp >= start_time)
    if end_time:
        q = q.filter(ObservationModel.acq_timestamp <= end_time)
    if data_origin:
        q = q.filter(ObservationModel.data_origin == data_origin)

    total = q.count()
    items = q.order_by(ObservationModel.acq_timestamp.desc()).offset(offset).limit(limit).all()
    return PaginatedObservations(total=total, limit=limit, offset=offset, items=items)


@router.get("/incidents", response_model=list[IncidentSummary])
def list_incidents(db: Session = Depends(get_db)):
    return db.query(IncidentModel).order_by(IncidentModel.priority_score.desc()).all()


@router.get("/incidents/{incident_id}", response_model=IncidentSummary)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(IncidentModel).filter_by(id=incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc


@router.get("/incidents/{incident_id}/observations", response_model=list[ObservationOut])
def get_incident_observations(incident_id: str, db: Session = Depends(get_db)):
    return (
        db.query(ObservationModel)
        .join(IncidentObservationModel, IncidentObservationModel.observation_id == ObservationModel.id)
        .filter(IncidentObservationModel.incident_id == incident_id)
        .order_by(ObservationModel.acq_timestamp.desc())
        .all()
    )


@router.get("/incidents/{incident_id}/timeline", response_model=list[SnapshotOut])
def get_incident_timeline(incident_id: str, db: Session = Depends(get_db)):
    return (
        db.query(IncidentSnapshotModel)
        .filter_by(incident_id=incident_id)
        .order_by(IncidentSnapshotModel.window_start.asc())
        .all()
    )


@router.get("/terrain/sources")
def get_terrain_sources():
    return COPERNICUS_GLO30_METADATA


@router.get("/incidents/{incident_id}/terrain")
def get_incident_terrain(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(IncidentModel).filter_by(id=incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return extract_multiscale_terrain(inc.centroid_lat, inc.centroid_lon)


@router.get("/incidents/{incident_id}/progression")
def get_incident_progression(incident_id: str, db: Session = Depends(get_db)):
    snaps = (
        db.query(IncidentSnapshotModel)
        .filter_by(incident_id=incident_id)
        .order_by(IncidentSnapshotModel.window_start.asc())
        .all()
    )
    if not snaps:
        raise HTTPException(status_code=404, detail="Incident snapshots not found")
    return analyze_incident_progression(snaps)


@router.get("/audit")
def list_audit_logs(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    logs = db.query(AuditLogModel).order_by(AuditLogModel.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "event_type": l.event_type,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "payload": l.payload,
            "created_at": l.created_at,
        }
        for l in logs
    ]
