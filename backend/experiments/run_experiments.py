import json
from datetime import datetime, timezone
from pathlib import Path

from app.analytics.research import detect_window_anomalies, forecast_next_window_activity
from app.analytics.tracking import process_incidents
from app.pipelines.ingest import run_ingestion
from app.storage.database import Base, SessionLocal, engine
from app.storage.models import IncidentModel, IncidentSnapshotModel


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(IncidentModel).count() == 0:
            run_ingestion(db, day_range=3, force_demo=True)
            process_incidents(db)

        incidents = db.query(IncidentModel).all()
        report_rows = []
        for inc in incidents:
            snaps = (
                db.query(IncidentSnapshotModel)
                .filter_by(incident_id=inc.id)
                .order_by(IncidentSnapshotModel.window_start.asc())
                .all()
            )
            windows = [
                {
                    "hotspot_count": float(s.hotspot_count),
                    "max_frp": float(s.max_frp),
                    "affected_area_km2": float(s.affected_area_km2),
                }
                for s in snaps
            ]
            anomalies = detect_window_anomalies(windows)
            forecast = forecast_next_window_activity(
                [s.hotspot_count for s in snaps],
                [s.max_frp for s in snaps],
            )
            report_rows.append(
                {
                    "persistent_key": inc.persistent_key,
                    "data_origin": inc.data_origin,
                    "windows": len(snaps),
                    "anomalies_detected": sum(1 for a in anomalies if a.is_anomaly),
                    "forecast_next_6h": forecast.predicted_count,
                    "interval_90": [forecast.interval_low, forecast.interval_high],
                    "model_mae": forecast.model_mae,
                    "baseline_mae": forecast.baseline_mae,
                    "interval_coverage": forecast.interval_coverage,
                }
            )

        out_dir = Path(__file__).parent
        artifact = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "experiments": report_rows,
        }
        (out_dir / "experiment_results.json").write_text(json.dumps(artifact, indent=2))
        print(json.dumps(artifact, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
