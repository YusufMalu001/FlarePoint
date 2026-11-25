import { Incident, Observation, Snapshot } from "@/types/flarepoint";

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
