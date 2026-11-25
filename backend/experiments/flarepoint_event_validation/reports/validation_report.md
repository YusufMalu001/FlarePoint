# FlarePoint Milestone 4 — Wildfire Event Validation Report

## 1. Study Scope & Data Sources
- **Region**: Northern California (`[-124.2, 39.5, -121.0, 42.0]`, `EPSG:32610`)
- **Period**: August 1–20, 2024
- **Satellite Source**: NASA FIRMS `VIIRS_SNPP_SP` (3,294 deduplicated observations)
- **Independent Reference Source**: NIFC WFIGS Interagency Fire Perimeters (2024, 4 active fires `>= 10 acres` in window)

## 2. Primary Validation Results (`eps = 5.0 km`, `max_temporal_gap = 24.0 h`)
| Metric | Value | Definition (Numerator / Denominator) |
| :--- | :--- | :--- |
| **Event Precision** | **0.7273** | 8 matched FlarePoint incidents / 11 total FlarePoint incidents |
| **Event Recall** | **0.5000** | 2 matched reference fires / 4 active WFIGS reference fires (`>= 10 acres`) |
| **Event F1** | **0.5926** | Harmonic mean of Precision (`0.7273`) and Recall (`0.5000`) |
| **Median Distance to Perimeter** | **0.0 km** | Median `EPSG:32610` distance from FlarePoint centroid to matched WFIGS perimeter (`n=8`) |
| **Mean Distance to Perimeter** | **1.794 km** | Mean `EPSG:32610` distance from FlarePoint centroid to matched WFIGS perimeter (`n=8`) |
| **Fragmented Reference Fires** | **2 / 2** | Park Fire (`2024-CABTU-013761`, 6 fragments) & Boise Fire (`2024-CASRF-000729`, 2 fragments) |
| **Merged FlarePoint Incidents** | **0 / 11** | FlarePoint incidents matching >1 reference fire |

## 3. Threshold Sensitivity (`eps_km` ∈ {3, 5, 10}, `temporal_gap_h` ∈ {12, 24, 48})
- Increasing `temporal_gap_h` from `24h` to `48h` (at `eps=5 km`) reduced fragmentation from **2** to **1** reference fire while keeping `merged_fps = 0` and `median_perim_dist_km = 0.0 km`.
- Decreasing `temporal_gap_h` to `12h` fragmented active fires into **29** FlarePoint incidents.

## 4. Limitations
- NIFC WFIGS is an agency perimeter record, not complete ground truth for small fires, prescribed burns, or non-wildfire thermal anomalies (3 unmatched FlarePoint incidents).
- Large megafires (e.g., Park Fire, 429,602.9 acres) span tens of kilometers and naturally fragment under a `5.0 km` DBSCAN radius.
