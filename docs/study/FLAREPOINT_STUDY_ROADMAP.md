# FlarePoint — Study Roadmap

## 7-Day Accelerated Preparation Plan
- **Day 1 (Foundations & Remote Sensing)**: Parts I–II (Chapters 1–8) — Understand what FlarePoint does, why hotspots ≠ fires, NASA FIRMS fields, MODIS vs. VIIRS, and WGS84 vs. UTM.
- **Day 2 (System Architecture & Pipeline)**: Parts III–IV (Chapters 9–16) — Trace an observation from `FirmsAdapter` → `validate_and_normalize_row` → `ObservationModel` → FastAPI → MapLibre.
- **Day 3 (Clustering & Continuity)**: Part V (Chapters 17–20) — Master Haversine DBSCAN, temporal splitting, `ContinuityEvent` fragment recovery, and merge safeguards.
- **Day 4 (Terrain & DEMs)**: Part VI (Chapters 21–30) — Understand Copernicus GLO-30, `rasterio` + `pyproj` UTM reprojection, Horn's 3×3 slope/aspect, TRI, TPI, Laplacian curvature, and centroid progression.
- **Day 5 (Research & Statistical Audit)**: Part IX (Chapters 37–43) — Study the Northern California terrain study, why `p = 0.0471` failed the robustness audit (`Moran's I = 0.184`, `73.8%` in 3 cells), and Milestone 4 WFIGS validation.
- **Day 6 (Testing, Failure Modes & Limitations)**: Parts XI–XII (Chapters 46–51) — Review all 25 `pytest` tests, failure modes, and defensible vs. indefensible claims.
- **Day 7 (Interview Defence & Walkthrough)**: Parts XIII–XIV (Chapters 52–59) — Practice the 30-second/2-minute/5-minute pitches, Q&A bank, and 5-minute live demo walkthrough.

## 14-Day Deep-Dive Plan
Spend 2 days per block above, reading the referenced source files side-by-side (`backend/app/analytics/clustering.py`, `continuity.py`, `terrain/derivatives.py`, `terrain/dem_provider.py`, `experiments/flarepoint_terrain_fire_study/audit/run_audit.py`, `experiments/flarepoint_event_validation/scripts/matching.py`) and running the offline reproduction commands locally.
