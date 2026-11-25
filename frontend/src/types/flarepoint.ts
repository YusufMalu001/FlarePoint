export interface PriorityRule {
  rule: string;
  value: number | string;
  points: number;
}

export interface Incident {
  id: string;
  persistent_key: string;
  first_seen_at: string;
  last_seen_at: string;
  status: string;
  centroid_lat: number;
  centroid_lon: number;
  footprint_geojson: GeoJSON.Geometry;
  affected_area_km2: number;
  hotspot_count: number;
  max_frp: number;
  mean_frp: number;
  cluster_confidence: number;
  priority_score: number;
  priority_tier: "CRITICAL" | "HIGH" | "MODERATE" | "LOW";
  priority_explanation: {
    rules: PriorityRule[];
    disclaimer: string;
  };
  weather_context: {
    source: string;
    temperature_c: number | null;
    relative_humidity_pct: number | null;
    wind_speed_kmh: number | null;
    wind_direction_deg: number | null;
  };
  land_cover_summary: Record<string, number>;
  data_origin: "REAL_FIRMS" | "SIMULATED_DEMO";
}

export interface Observation {
  id: string;
  source_sensor: string;
  satellite: string;
  acq_timestamp: string;
  latitude: number;
  longitude: number;
  brightness: number;
  frp: number;
  confidence_raw: string;
  confidence_norm: number;
  daynight: string;
  data_origin: "REAL_FIRMS" | "SIMULATED_DEMO";
}

export interface Snapshot {
  window_start: string;
  window_end: string;
  hotspot_count: number;
  max_frp: number;
  mean_frp: number;
  affected_area_km2: number;
  centroid_lat: number;
  centroid_lon: number;
}

export interface TerrainScale {
  scale_m: number;
  elev_mean_m: number;
  elev_range_m: number;
  slope_mean_deg: number | null;
  slope_std_deg: number | null;
  aspect_circ_mean_deg: number | null;
  tri_mean_m: number | null;
  tpi_mean_m: number | null;
}

export interface TerrainContext {
  metadata: {
    dataset: string;
    source_type: "REAL_DEM" | "SYNTHETIC_DEM" | "NO_TERRAIN_AVAILABLE";
    is_synthetic: boolean;
    analysis_crs?: string;
  };
  center_point: {
    elevation_m: number;
    slope_deg: number | null;
    aspect_deg: number | null;
    tri_m: number | null;
    tpi_m: number | null;
    curvature_1_per_m: number | null;
  } | null;
  multiscale: TerrainScale[];
}

export interface ProgressionAnalysis {
  label: string;
  disclaimer: string;
  transitions: {
    from_window: string;
    to_window: string;
    displacement_km: number;
    bearing_deg: number;
    elapsed_hours: number;
    elevation_delta_m: number | null;
    classification: string;
    quality_flags?: string[];
  }[];
}

export interface AuditLogEntry {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  payload: Record<string, unknown>;
  created_at: string;
}
