# Terrain-Associated Patterns in Satellite-Detected Wildfire Activity: A Multi-Scale Geospatial Analysis

## 1. Abstract & Research Question
This exploratory observational study examines how satellite-detected wildfire activity (NASA FIRMS `VIIRS_SNPP_SP`, August 1–20, 2024) varies across Copernicus DEM GLO-30 terrain characteristics (elevation, slope, aspect, TRI) in Northern California (`[-124.2, 39.5, -121.0, 42.0]`, `EPSG:32610`). Across **293** valid 15 km × 15 km land grid cells, **3,294** deduplicated VIIRS detections (**11** spatiotemporal incident clusters) fell within **19** grid cells.

## 2. Methods
- **Background Spatial Denominator**: 293 metric grid cells (`15 km × 15 km` in `EPSG:32610`), including zero-detection cells.
- **Terrain Source**: Real Copernicus DEM GLO-30 tiles (`REAL_DEM`, `strict_real_data=True`), bilinearly reprojected to `EPSG:32610` (`30 m`).
- **Statistical Tests**: Kruskal-Wallis H-test across elevation, slope, and aspect (excluding `slope < 5°`), Spearman rank correlation for TRI at point and `3000 m` scales, and Benjamini-Hochberg FDR correction ($\alpha = 0.05$).

## 3. Results (Observed)
| Hypothesis | Test | Statistic | Raw p-value | FDR p-value | Effect Size |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **H1 (Elevation)** | Kruskal-Wallis (7 classes) | `H = 16.9609` | `0.0094` | **`0.0471`** | `ε² = 0.0383` |
| **H2 (Slope)** | Kruskal-Wallis (4 classes) | `H = 5.5723` | `0.1344` | `0.1680` | `ε² = 0.0089` |
| **H3 (Aspect, slope ≥ 5°)** | Kruskal-Wallis (8 sectors, n=216) | `H = 6.2624` | `0.5095` | `0.5095` | `ε² = 0.0000` |
| **H4 (TRI)** | Spearman | `ρ = -0.0957` | `0.1019` | `0.1680` | — |
| **H5 (TRI 3000 m)** | Spearman | `ρ = -0.0955` | `0.1030` | `0.1680` | — |

- **Sensitivity (High/Nominal Confidence Only)**: Elevation association remained significant (`H = 14.4747`, `p = 0.0248`, `ε² = 0.0296`).

## 4. Limitations & Conclusions
- Only **19 of 293** grid cells contained detections during the 20-day window (reflecting 11 localized fire incidents), so spatial autocorrelation is high and conclusions are strictly exploratory.
- Elevation showed a modest statistically significant association after FDR correction (`p_fdr = 0.0471`), whereas slope, aspect, and TRI did not.
- Satellite detection counts do not measure wildfire ignition probability, and area normalization does not remove satellite coverage/cloud bias.
