# FlarePoint — Geospatial Wildfire Intelligence Platform

FlarePoint ingests satellite active-fire detections (NASA FIRMS or deterministic `SIMULATED_DEMO` mode), normalizes and deduplicates observations, clusters detections with Haversine DBSCAN, tracks persistent incidents over time, and presents an operational 2D/3D MapLibre GL interface.

## Architecture & Data Source

- **NASA FIRMS Area CSV API**: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{source}/{area}/{day_range}`
  - Supported sources: `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `MODIS_NRT`
  - Rate limit: 5,000 transactions / 10-minute sliding window per `MAP_KEY`
  - Demo mode (`DEMO_MODE=true` or empty `NASA_FIRMS_MAP_KEY`) generates deterministic `SIMULATED_DEMO` observations.
- **Database Indexes**:
  - `observations.dedup_hash` (UNIQUE): enforces idempotent ingestion.
  - `ix_observations_lat_lon_ts`: accelerates bounding-box + time-window queries.
  - `ix_observations_origin_ts`: separates `REAL_FIRMS` from `SIMULATED_DEMO` queries.

## Running Locally

```bash
docker compose up --build
```

- **Frontend**: `http://localhost:3000`
- **Backend API Docs**: `http://localhost:8000/docs`

## Running Backend Tests

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest -v
```
