# Revised Scientific Interpretation (Statistical & Spatial Audit)

## Conclusion: **C — Elevation association is not supported after correcting for spatial dependence and binning sensitivity.**

### Key Audit Findings
1. **Sampling Unit & Extreme Concentration**:
   - H1–H5 used `n = 293` 15 km × 15 km grid cells (not raw detections), with `274` zero-detection cells and `19` active cells.
   - However, **40.1%** of all 3,294 detections occurred in **1 cell**, and **73.8%** occurred in just **3 cells**.
2. **Spatial Autocorrelation (Moran's I, 25 km band, `EPSG:32610`)**:
   - `detection_count`: `I = 0.184`, `p_perm = 0.002`
   - `elevation_m`: `I = 0.6425`, `p_perm = 0.002`
   - Neighboring 15 km cells violate the independence assumption of Kruskal-Wallis.
3. **Robustness Collapse**:
   - **Original H1 (7 elevation classes, 15 km)**: `H = 16.9609`, `p = 0.0094` (FDR `0.0471`, `ε² = 0.0383`)
   - **Presence/Absence (Mann-Whitney U, 19 vs 274 cells)**: `U = 1958.0`, `p = 0.0711` (not significant)
   - **Coarser 4 Elevation Bands (`<500, 500–1000, 1000–1500, 1500+`)**: `H = 3.645`, `p = 0.3024` (not significant)
   - **30 km Spatial Blocks (`n = 80`)**: `H = 3.4989`, `p = 0.3209` (not significant)

### Scientific Statement
The narrow FDR-adjusted `p = 0.0471` in the initial study is an artifact of fine 7-bin partitioning, spatial autocorrelation, and 3 high-count fire cells rather than a generalizable elevation effect across Northern California during August 1–20, 2024.
