# FlarePoint Wildfire Event Association and Detection Validation

## Primary Objective
Evaluate the spatial and temporal correspondence between satellite-derived FlarePoint incidents (`VIIRS_SNPP_SP` clustered with Haversine DBSCAN) and independently documented wildfire perimeters (NIFC WFIGS Interagency Fire Perimeters, 2024).

## Secondary Objectives
- Measure **event-level precision, recall, and F1** (against documented reference perimeters active during the evaluation window).
- Measure **spatial accuracy** (centroid-to-centroid distance, centroid-to-perimeter distance in `EPSG:32610`, and fraction of detections inside perimeter).
- Quantify **incident fragmentation** (1 reference fire → multiple FlarePoint incidents) and **incident merging** (1 FlarePoint incident → multiple reference fires).
- Evaluate **threshold sensitivity** across `dbscan_eps_km` (`3, 5, 10 km`) and `max_temporal_gap_hours` (`12, 24, 48 h`).

## Reference Dataset Limitations
NIFC WFIGS perimeters are independent agency records, not complete ground truth for every thermal anomaly. Small fires, prescribed burns, agricultural/industrial heat sources, or unmapped incidents may appear as `UNMATCHED_FLAREPOINT`.
