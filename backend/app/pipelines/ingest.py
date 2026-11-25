from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.adapters.demo import DemoAdapter
from app.adapters.firms import FirmsAdapter
from app.core.config import settings
from app.domain.models import DataOrigin
from app.pipelines.normalize import normalize_row
from app.storage.models import AuditLogModel, IngestionRunModel, ObservationModel


def run_ingestion(
    db: Session,
    source: str | None = None,
    bbox: str | None = None,
    day_range: int = 3,
    force_demo: bool | None = None,
) -> IngestionRunModel:
    """Fetch, normalize, validate, deduplicate, and store satellite observations."""
    use_demo = settings.demo_mode if force_demo is None else force_demo
    if not settings.nasa_firms_map_key:
        use_demo = True

    origin = DataOrigin.SIMULATED_DEMO if use_demo else DataOrigin.REAL_FIRMS
    src = source or settings.nasa_firms_default_source
    area = bbox or settings.nasa_firms_default_bbox

    run = IngestionRunModel(
        source=src,
        area_bbox=area,
        status="RUNNING",
        data_origin=origin.value,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        if use_demo:
            raw_rows = DemoAdapter().generate_observations(day_range=day_range)
        else:
            raw_rows = FirmsAdapter().fetch_area_csv(source=src, bbox=area, day_range=day_range)

        run.records_fetched = len(raw_rows)
        inserted = 0

        for row in raw_rows:
            obs = normalize_row(row, source_sensor=src, origin=origin)
            if obs is None:
                continue

            exists = db.query(ObservationModel.id).filter_by(dedup_hash=obs.dedup_hash).first()
            if exists:
                continue

            db.add(
                ObservationModel(
                    ingestion_run_id=run.id,
                    source_sensor=obs.source_sensor,
                    satellite=obs.satellite,
                    acq_timestamp=obs.acq_timestamp,
                    latitude=obs.latitude,
                    longitude=obs.longitude,
                    brightness=obs.brightness,
                    frp=obs.frp,
                    confidence_raw=obs.confidence_raw,
                    confidence_norm=obs.confidence_norm,
                    daynight=obs.daynight,
                    dedup_hash=obs.dedup_hash,
                    data_origin=obs.data_origin.value,
                )
            )
            inserted += 1

        run.records_inserted = inserted
        run.status = "COMPLETED"
        run.completed_at = datetime.now(timezone.utc)

        db.add(
            AuditLogModel(
                event_type="INGESTION_COMPLETED",
                entity_type="ingestion_run",
                entity_id=run.id,
                payload={
                    "source": src,
                    "data_origin": origin.value,
                    "fetched": run.records_fetched,
                    "inserted": inserted,
                },
            )
        )
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        run.status = "FAILED"
        run.error_message = str(exc)
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise
