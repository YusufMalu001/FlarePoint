# FlarePoint — Repository Evidence Index

Every technical and scientific claim in the FlarePoint Technical Study Handbook is mapped below to its exact implementation, experiment artifact, and verification status.

| Claim / Capability | Status | Evidence in Repository |
| :--- | :--- | :--- |
| **NASA FIRMS Area CSV Ingestion (`VIIRS_SNPP_NRT/SP`, `MODIS_NRT`)** | Implemented & Live-Verified | `backend/app/adapters/firms.py`, `backend/experiments/live_firms_e2e_validation.json` |
| **Deterministic Demo Mode (`SIMULATED_DEMO`)** | Implemented & Tested | `backend/app/adapters/demo.py`, `backend/tests/test_pipeline.py` |
| **Schema Validation & No-Invented-Values Normalization** | Implemented & Tested | `backend/app/pipelines/normalize.py` (`validate_and_normalize_row`), `test_validation_and_no_invented_values` |
| **SHA-256 Deduplication & Idempotent Ingestion** | Implemented & Tested | `backend/app/pipelines/ingest.py`, `ObservationModel.dedup_hash`, `test_idempotency_and_api_filtering` |
| **Spatiotemporal Haversine DBSCAN + 24h Temporal Split** | Implemented & Tested | `backend/app/analytics/clustering.py` (`cluster_observations_spatiotemporal`), `backend/tests/test_geospatial.py` |
| **1-to-1 Weighted Incident Association & Lifecycle** | Implemented & Tested | `backend/app/analytics/tracking.py` (`compute_association_score`, `evaluate_lifecycle_status`) |
| **Fragmentation-Aware Incident Continuity (`ContinuityEvent`)** | Implemented & Tested | `backend/app/analytics/continuity.py` (`associate_incidents_to_events`), `backend/tests/test_continuity.py` |
| **Explainable Rule-Based Prioritization** | Implemented & Tested | `backend/app/analytics/prioritization.py` (`compute_priority`) |
| **Applied ML (IsolationForest Anomaly & RF Activity Forecast)** | Experimental / Tested | `backend/app/analytics/research.py`, `backend/experiments/experiment_results.json` |
| **Copernicus DEM GLO-30 Retrieval, Cache & UTM Reprojection** | Implemented & Live-Verified | `backend/app/terrain/dem_provider.py`, `backend/experiments/live_dem_validation.json` |
| **Horn 3×3 Slope/Aspect (8 Directions), TRI, TPI, Curvature** | Implemented & Tested | `backend/app/terrain/derivatives.py`, `backend/tests/test_terrain.py` |
| **Multi-Scale Terrain (`250m–3000m`) & Centroid Progression** | Implemented & Live-Verified | `backend/app/terrain/extractor.py`, `backend/app/terrain/progression.py` |
| **Terrain–Wildfire Spatial Study & Robustness Audit** | Executed on Real Data | `backend/experiments/flarepoint_terrain_fire_study/statistical_results/results.json`, `audit/audit_summary.json` |
| **Wildfire Event Validation vs. NIFC WFIGS (2024)** | Executed on Real Data | `backend/experiments/flarepoint_event_validation/results/validation_summary.json`, `sensitivity_results.csv` |
| **FastAPI REST API & Alembic Migrations** | Implemented & Tested | `backend/app/api/routes.py`, `backend/alembic/versions/0001_initial_schema.py` |
| **Next.js + MapLibre GL Workstation UI** | Implemented & Built | `frontend/src/app/page.tsx`, `MapViewport.tsx`, `LeftInspectorDrawer.tsx`, `LayersPanel.tsx` |
