"use client";

import { useEffect, useState, useCallback } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { LeftIconRail } from "@/components/layout/LeftIconRail";
import { LeftInspectorDrawer } from "@/components/inspector/LeftInspectorDrawer";
import { MapViewport } from "@/components/map/MapViewport";
import { LayersPanel, BaseMapId } from "@/components/layers/LayersPanel";
import { fetchIncidents, fetchObservations, fetchTimeline, triggerIngest } from "@/lib/api";
import { Incident, Observation, Snapshot } from "@/types/flarepoint";

export default function FlarePointPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [timeline, setTimeline] = useState<Snapshot[]>([]);
  const [activeSection, setActiveSection] = useState<"map" | "analytics" | "alerts" | "audit">("map");
  const [searchQuery, setSearchQuery] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Layer states
  const [baseMap, setBaseMap] = useState<BaseMapId>("satellite");
  const [showFootprints, setShowFootprints] = useState(true);
  const [showHotspots, setShowHotspots] = useState(true);
  const [footprintOpacity, setFootprintOpacity] = useState(0.35);
  const [highlightLatest, setHighlightLatest] = useState(false);

  const loadIncidents = useCallback(async () => {
    try {
      const data = await fetchIncidents();
      setIncidents(data);
      if (data.length > 0 && !selectedIncident) {
        setSelectedIncident(data[0]);
      }
    } catch (err) {
      console.error("Failed to load incidents:", err);
    }
  }, [selectedIncident]);

  useEffect(() => {
    loadIncidents();
  }, [loadIncidents]);

  useEffect(() => {
    if (!selectedIncident) return;
    fetchObservations(selectedIncident.id).then(setObservations).catch(console.error);
    fetchTimeline(selectedIncident.id).then(setTimeline).catch(console.error);
  }, [selectedIncident?.id]);

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

      <div className="flex-1 flex min-h-0">
        <LeftIconRail activeSection={activeSection} onSelectSection={setActiveSection} />

        <LeftInspectorDrawer
          incidents={filteredIncidents}
          selectedIncident={selectedIncident}
          onSelectIncident={setSelectedIncident}
          observations={observations}
          timeline={timeline}
          highlightLatest={highlightLatest}
          onToggleHighlightLatest={() => setHighlightLatest(!highlightLatest)}
        />

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
