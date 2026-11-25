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
