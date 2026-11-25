"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { Plus, Minus, Compass, Box, Calendar } from "lucide-react";
import { Incident, Observation } from "@/types/flarepoint";
import { BaseMapId } from "@/components/layers/LayersPanel";

interface MapViewportProps {
  incidents: Incident[];
  selectedIncident: Incident | null;
  observations: Observation[];
  baseMap: BaseMapId;
  showFootprints: boolean;
  showHotspots: boolean;
  footprintOpacity: number;
  highlightLatest: boolean;
  onSelectIncident: (inc: Incident) => void;
}

const TILE_URLS: Record<BaseMapId, string> = {
  satellite: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  dark: "https://a.basemaps.cartocdn.com/dark_all/{z}/{y}/{x}.png",
  bright: "https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{y}/{x}.png",
  topographic: "https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
};

export function MapViewport({
  incidents,
  selectedIncident,
  observations,
  baseMap,
  showFootprints,
  showHotspots,
  footprintOpacity,
  highlightLatest,
  onSelectIncident,
}: MapViewportProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [is3D, setIs3D] = useState(true);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          basemap: {
            type: "raster",
            tiles: [TILE_URLS[baseMap]],
            tileSize: 256,
          },
        },
        layers: [{ id: "basemap-layer", type: "raster", source: "basemap" }],
      },
      center: selectedIncident
        ? [selectedIncident.centroid_lon, selectedIncident.centroid_lat]
        : [32.22333, 36.48989],
      zoom: 10,
      pitch: 45,
    });

    map.on("load", () => {
      map.addSource("footprints", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "footprints-fill",
        type: "fill",
        source: "footprints",
        paint: {
          "fill-color": "#ef4444",
          "fill-opacity": footprintOpacity,
        },
      });
      map.addLayer({
        id: "footprints-outline",
        type: "line",
        source: "footprints",
        paint: {
          "line-color": "#fca5a5",
          "line-width": 1.5,
        },
      });

      map.addSource("hotspots", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "hotspots-circle",
        type: "circle",
        source: "hotspots",
        paint: {
          "circle-radius": ["case", ["==", ["get", "isLatest"], true], 6, 4.5],
          "circle-color": [
            "case",
            [">=", ["get", "frp"], 50],
            "#ef4444",
            [">=", ["get", "frp"], 15],
            "#f59e0b",
            "#38bdf8",
          ],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1,
        },
      });
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update base map tiles
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const src = map.getSource("basemap") as maplibregl.RasterTileSource | undefined;
    if (src && typeof src.setTiles === "function") {
      src.setTiles([TILE_URLS[baseMap]]);
    }
  }, [baseMap]);

  // Fly to selected incident
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedIncident) return;
    map.flyTo({
      center: [selectedIncident.centroid_lon, selectedIncident.centroid_lat],
      zoom: 11,
      pitch: is3D ? 45 : 0,
      duration: 900,
    });
  }, [selectedIncident?.id, is3D]);

  // Update footprints & hotspots
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const fpSrc = map.getSource("footprints") as maplibregl.GeoJSONSource | undefined;
    if (fpSrc) {
      fpSrc.setData({
        type: "FeatureCollection",
        features: showFootprints
          ? incidents.map((inc) => ({
              type: "Feature",
              properties: { id: inc.id, key: inc.persistent_key },
              geometry: inc.footprint_geojson,
            }))
          : [],
      });
    }

    if (map.getLayer("footprints-fill")) {
      map.setPaintProperty("footprints-fill", "fill-opacity", footprintOpacity);
    }

    const hsSrc = map.getSource("hotspots") as maplibregl.GeoJSONSource | undefined;
    if (hsSrc) {
      const latestCutoff = Date.now() - 12 * 3600 * 1000;
      hsSrc.setData({
        type: "FeatureCollection",
        features: showHotspots
          ? observations.map((o) => ({
              type: "Feature",
              properties: {
                id: o.id,
                frp: o.frp,
                isLatest: highlightLatest && new Date(o.acq_timestamp).getTime() >= latestCutoff,
              },
              geometry: { type: "Point", coordinates: [o.longitude, o.latitude] },
            }))
          : [],
      });
    }
  }, [incidents, observations, showFootprints, showHotspots, footprintOpacity, highlightLatest]);

  return (
    <div className="relative flex-1 h-full bg-[#060e12]">
      <div ref={containerRef} className="w-full h-full" />

      {/* Top-Left 3D / Mode Pill */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        <button
          onClick={() => setIs3D(!is3D)}
          className="px-3 py-1 rounded-full bg-[#0c181d]/90 border border-[#1c333c] text-xs text-slate-200 flex items-center gap-1.5 backdrop-blur"
        >
          <Box className="w-3.5 h-3.5 text-teal-400" />
          <span>{is3D ? "3D Terrain" : "2D Flat"}</span>
        </button>
      </div>

      {/* Bottom-Center Time-Window Scrubber */}
      {selectedIncident && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 bg-[#0c181d]/90 border border-[#1c333c] rounded-md px-3 py-1.5 flex items-center gap-2.5 text-[11px] text-slate-200 backdrop-blur">
          <Calendar className="w-3.5 h-3.5 text-teal-400" />
          <span className="font-mono">
            {new Date(selectedIncident.first_seen_at).toISOString().slice(0, 16).replace("T", " ")}
            {" — "}
            {new Date(selectedIncident.last_seen_at).toISOString().slice(0, 16).replace("T", " ")} UTC
          </span>
        </div>
      )}

      {/* Bottom-Right Map Controls */}
      <div className="absolute bottom-4 right-3 z-10 flex flex-col gap-1">
        <button
          onClick={() => mapRef.current?.zoomIn()}
          className="w-8 h-8 rounded bg-[#0c181d]/90 border border-[#1c333c] flex items-center justify-center text-slate-200 hover:bg-[#112128]"
          title="Zoom in"
        >
          <Plus className="w-4 h-4" />
        </button>
        <button
          onClick={() => mapRef.current?.zoomOut()}
          className="w-8 h-8 rounded bg-[#0c181d]/90 border border-[#1c333c] flex items-center justify-center text-slate-200 hover:bg-[#112128]"
          title="Zoom out"
        >
          <Minus className="w-4 h-4" />
        </button>
        <button
          onClick={() =>
            selectedIncident &&
            mapRef.current?.flyTo({
              center: [selectedIncident.centroid_lon, selectedIncident.centroid_lat],
              zoom: 11,
            })
          }
          className="w-8 h-8 rounded bg-[#0c181d]/90 border border-[#1c333c] flex items-center justify-center text-slate-200 hover:bg-[#112128]"
          title="Recenter on incident"
        >
          <Compass className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
