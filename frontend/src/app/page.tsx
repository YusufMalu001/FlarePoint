"use client";

import { useEffect, useState, useCallback } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { LeftIconRail } from "@/components/layout/LeftIconRail";
import { LeftInspectorDrawer } from "@/components/inspector/LeftInspectorDrawer";
import { MapViewport } from "@/components/map/MapViewport";
import { LayersPanel, BaseMapId } from "@/components/layers/LayersPanel";
import {
  fetchAuditLogs,
  fetchIncidents,
  fetchObservations,
  fetchProgression,
  fetchTerrain,
  fetchTimeline,
  triggerIngest,
} from "@/lib/api";
import {
  AuditLogEntry,
  Incident,
  Observation,
  ProgressionAnalysis,
  Snapshot,
  TerrainContext,
} from "@/types/flarepoint";

export default function FlarePointPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [timeline, setTimeline] = useState<Snapshot[]>([]);
  const [terrain, setTerrain] = useState<TerrainContext | null>(null);
  const [progression, setProgression] = useState<ProgressionAnalysis | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [activeSection, setActiveSection] = useState<"map" | "analytics" | "alerts" | "audit">("map");
  const [searchQuery, setSearchQuery] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Layer states
  const [baseMap, setBaseMap] = useState<BaseMapId>("satellite");
  const [showFootprints, setShowFootprints] = useState(true);
  const [showHotspots, setShowHotspots] = useState(true);
  const [footprintOpacity, setFootprintOpacity] = useState(0.35);
  const [highlightLatest, setHighlightLatest] = useState(false);

  const loadIncidents = useCallback(async () => {
    try {
      setErrorMsg(null);
      const data = await fetchIncidents();
      setIncidents(data);
      if (data.length > 0 && !selectedIncident) {
        setSelectedIncident(data[0]);
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to reach FlarePoint API");
    }
  }, [selectedIncident]);

  useEffect(() => {
    loadIncidents();
  }, [loadIncidents]);

  useEffect(() => {
    if (!selectedIncident) return;
    fetchObservations(selectedIncident.id).then(setObservations).catch(console.error);
    fetchTimeline(selectedIncident.id).then(setTimeline).catch(console.error);
    fetchTerrain(selectedIncident.id).then(setTerrain).catch(console.error);
    fetchProgression(selectedIncident.id).then(setProgression).catch(console.error);
  }, [selectedIncident?.id]);

  useEffect(() => {
    if (activeSection === "audit") {
      fetchAuditLogs().then(setAuditLogs).catch(console.error);
    }
  }, [activeSection]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await triggerIngest();
      await loadIncidents();
    } finally {
      setIsRefreshing(false);
    }
  };

  const filteredIncidents = incidents.filter((inc) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      inc.persistent_key.toLowerCase().includes(q) ||
      `${inc.centroid_lat.toFixed(2)},${inc.centroid_lon.toFixed(2)}`.includes(q)
    );
  });

  const dataOrigin = incidents[0]?.data_origin || "SIMULATED_DEMO";

  return (
    <div className="h-screen w-screen flex flex-col bg-[#081216] overflow-hidden">
      <TopBar
        incidentCount={incidents.length}
        dataOrigin={dataOrigin}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      {errorMsg && (
        <div className="bg-red-950/90 border-b border-red-500/50 px-4 py-1.5 text-xs text-red-200 flex items-center justify-between">
          <span>API Error: {errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="underline text-red-300">
            Dismiss
          </button>
        </div>
      )}

      <div className="flex-1 flex min-h-0">
        <LeftIconRail activeSection={activeSection} onSelectSection={setActiveSection} />

        <LeftInspectorDrawer
          incidents={filteredIncidents}
          selectedIncident={selectedIncident}
          onSelectIncident={setSelectedIncident}
          observations={observations}
          timeline={timeline}
          terrain={terrain}
          progression={progression}
          highlightLatest={highlightLatest}
          onToggleHighlightLatest={() => setHighlightLatest(!highlightLatest)}
        />

        {activeSection === "alerts" && (
          <div className="w-72 bg-[#0c181d] border-r border-[#1c333c] p-3 text-xs overflow-y-auto shrink-0">
            <div className="font-semibold text-slate-100 mb-2">Rule-Derived Priority Queue</div>
            <div className="space-y-2">
              {incidents.map((inc) => (
                <button
                  key={inc.id}
                  onClick={() => {
                    setSelectedIncident(inc);
                    setActiveSection("map");
                  }}
                  className="w-full text-left p-2 rounded bg-[#112128] border border-[#1c333c] hover:border-teal-400"
                >
                  <div className="flex justify-between font-mono">
                    <span className="text-slate-100">{inc.persistent_key}</span>
                    <span className="text-amber-300">{inc.priority_tier} ({inc.priority_score})</span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1">
                    {inc.hotspot_count} hotspots • Max FRP {inc.max_frp} MW
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {activeSection === "audit" && (
          <div className="w-80 bg-[#0c181d] border-r border-[#1c333c] p-3 text-xs overflow-y-auto shrink-0">
            <div className="font-semibold text-slate-100 mb-2">Provenance & Audit Trail</div>
            <div className="space-y-1.5">
              {auditLogs.map((log) => (
                <div key={log.id} className="p-2 rounded bg-[#112128] border border-[#1c333c] text-[10px]">
                  <div className="font-mono text-teal-300">{log.event_type}</div>
                  <div className="text-slate-400">{new Date(log.created_at).toISOString()}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <MapViewport
          incidents={filteredIncidents}
          selectedIncident={selectedIncident}
          observations={observations}
          baseMap={baseMap}
          showFootprints={showFootprints}
          showHotspots={showHotspots}
          footprintOpacity={footprintOpacity}
          highlightLatest={highlightLatest}
          onSelectIncident={setSelectedIncident}
        />

        <LayersPanel
          baseMap={baseMap}
          onBaseMapChange={setBaseMap}
          showFootprints={showFootprints}
          onToggleFootprints={() => setShowFootprints(!showFootprints)}
          showHotspots={showHotspots}
          onToggleHotspots={() => setShowHotspots(!showHotspots)}
          footprintOpacity={footprintOpacity}
          onOpacityChange={setFootprintOpacity}
          activeIncidentCount={filteredIncidents.length}
        />
      </div>
    </div>
  );
}
