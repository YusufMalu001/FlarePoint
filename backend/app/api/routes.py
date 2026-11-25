from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analytics.tracking import process_incidents
from app.api.schemas import (
    HealthResponse,
    IncidentSummary,
    IngestRequest,
    IngestResponse,
    ObservationOut,
    SnapshotOut,
)
from app.core.config import settings
from app.pipelines.ingest import run_ingestion
from app.storage.database import get_db
from app.storage.models import (
    AuditLogModel,
    IncidentModel,
    IncidentObservationModel,
    IncidentSnapshotModel,
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


@router.post("/ingest/run", response_model=IngestResponse)
def trigger_ingest(req: IngestRequest, db: Session = Depends(get_db)):
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
        records_inserted=run.records_inserted,
        incidents_active=len(incidents),
    )


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
    obs = (
        db.query(ObservationModel)
        .join(IncidentObservationModel, IncidentObservationModel.observation_id == ObservationModel.id)
        .filter(IncidentObservationModel.incident_id == incident_id)
        .order_by(ObservationModel.acq_timestamp.desc())
        .all()
    )
    return obs


@router.get("/incidents/{incident_id}/timeline", response_model=list[SnapshotOut])
def get_incident_timeline(incident_id: str, db: Session = Depends(get_db)):
    return (
        db.query(IncidentSnapshotModel)
        .filter_by(incident_id=incident_id)
        .order_by(IncidentSnapshotModel.window_start.asc())
        .all()
    )


@router.get("/audit")
def list_audit_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = (
        db.query(AuditLogModel)
        .order_by(AuditLogModel.created_at.desc())
        .limit(limit)
        .all()
    )
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
