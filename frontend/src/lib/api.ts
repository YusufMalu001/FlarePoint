import {
  AuditLogEntry,
  Incident,
  Observation,
  ProgressionAnalysis,
  Snapshot,
  TerrainContext,
} from "@/types/flarepoint";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchIncidents(): Promise<Incident[]> {
  const res = await fetch(`${API_BASE}/api/v1/incidents`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch incidents");
  return res.json();
}

export async function fetchObservations(incidentId: string): Promise<Observation[]> {
  const res = await fetch(`${API_BASE}/api/v1/incidents/${incidentId}/observations`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch observations");
  return res.json();
}

export async function fetchTimeline(incidentId: string): Promise<Snapshot[]> {
  const res = await fetch(`${API_BASE}/api/v1/incidents/${incidentId}/timeline`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch timeline");
  return res.json();
}

export async function triggerIngest(): Promise<void> {
  await fetch(`${API_BASE}/api/v1/ingest/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ day_range: 3 }),
  });
}

export async function fetchTerrain(incidentId: string): Promise<TerrainContext> {
  const res = await fetch(`${API_BASE}/api/v1/incidents/${incidentId}/terrain`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch terrain context");
  return res.json();
}

export async function fetchProgression(incidentId: string): Promise<ProgressionAnalysis> {
  const res = await fetch(`${API_BASE}/api/v1/incidents/${incidentId}/progression`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch progression");
  return res.json();
}

export async function fetchAuditLogs(): Promise<AuditLogEntry[]> {
  const res = await fetch(`${API_BASE}/api/v1/audit?limit=30`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch audit logs");
  return res.json();
}
