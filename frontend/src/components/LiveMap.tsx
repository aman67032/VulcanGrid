"use client";

import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, Polygon, GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";
import * as h3 from "h3-js";
import { AlertItem, FacilityFeature, HotspotClass } from "../types";

interface LiveMapProps {
  alerts: AlertItem[];
  selectedAlertId: string | null;
  onSelectAlert: (id: string) => void;
  showPlume: boolean;
}

// Map Recenter Helper Component
const MapRecenter: React.FC<{ selectedAlert: AlertItem | null }> = ({ selectedAlert }) => {
  const map = useMap();
  useEffect(() => {
    if (selectedAlert) {
      map.flyTo([selectedAlert.latitude, selectedAlert.longitude], 12, {
        duration: 1.5,
      });
    }
  }, [selectedAlert, map]);
  return null;
};

export default function LiveMap({
  alerts,
  selectedAlertId,
  onSelectAlert,
  showPlume,
}: LiveMapProps) {
  const [facilities, setFacilities] = useState<FacilityFeature[]>([]);
  const [plumeGeoJson, setPlumeGeoJson] = useState<any>(null);

  // Fetch industrial & solar polygons
  useEffect(() => {
    fetch("/api/facilities")
      .then((res) => res.json())
      .then((data) => {
        if (data.features) setFacilities(data.features);
      })
      .catch((err) => console.error("Failed fetching facility boundaries:", err));
  }, []);

  const selectedAlert = alerts.find((a) => a.id === selectedAlertId) || null;

  // Fetch Plume polygon when showPlume is active
  useEffect(() => {
    if (showPlume && selectedAlert && selectedAlert.predicted_class === "industrial_fire") {
      fetch(`/api/plume/${selectedAlert.id}`)
        .then((res) => res.json())
        .then((data) => setPlumeGeoJson(data))
        .catch((err) => console.error("Failed fetching plume polygon:", err));
    } else {
      setPlumeGeoJson(null);
    }
  }, [showPlume, selectedAlert]);

  const getMarkerColor = (cls: HotspotClass) => {
    switch (cls) {
      case "controlled_flare":
        return "#10B981"; // Emerald Green
      case "industrial_fire":
        return "#EF4444"; // Crimson Red
      case "forest_fire":
        return "#F97316"; // Vivid Orange
      case "false_alarm":
        return "#6B7280"; // Slate Grey
      default:
        return "#3B82F6";
    }
  };

  return (
    <div className="relative w-full h-full bg-slate-950">
      <MapContainer
        center={[22.5, 78.5]} // Center over India
        zoom={5}
        zoomControl={false}
        className="w-full h-full z-10"
      >
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          attribution='&copy; <a href="https://www.esri.com/">Esri</a>, HERE, Garmin, &copy; OpenStreetMap'
          maxZoom={16}
        />
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}"
          attribution=""
          maxZoom={16}
        />

        <MapRecenter selectedAlert={selectedAlert} />

        {/* Industrial & Solar Facility Polygons */}
        {facilities.map((fac, idx) => {
          // Convert GeoJSON coordinates [lon, lat] to Leaflet [lat, lon]
          const coords = fac.geometry.coordinates[0].map(([lon, lat]) => [lat, lon] as [number, number]);
          const isSolar = fac.properties.facility_type === "solar_farm";

          return (
            <Polygon
              key={idx}
              positions={coords}
              pathOptions={{
                color: isSolar ? "#EAB308" : "#3B82F6", // Yellow for solar, Blue for industrial
                weight: 2,
                dashArray: isSolar ? "4, 4" : undefined,
                fillColor: isSolar ? "#EAB308" : "#3B82F6",
                fillOpacity: 0.15,
              }}
            >
              <Popup>
                <div className="font-mono text-xs p-1">
                  <strong className="text-slate-100">{fac.properties.name}</strong>
                  <br />
                  <span className="text-slate-400 capitalize">{fac.properties.facility_type.replace("_", " ")}</span>
                </div>
              </Popup>
            </Polygon>
          );
        })}

        {/* Gaussian Plume Dispersion Overlay */}
        {plumeGeoJson && (
          <GeoJSON
            key={JSON.stringify(plumeGeoJson)}
            data={plumeGeoJson}
            style={{
              color: "#EF4444",
              weight: 2,
              dashArray: "6, 6",
              fillColor: "#EF4444",
              fillOpacity: 0.35,
            }}
          />
        )}

        {/* Hotspot Markers & H3 Hexagon Boundaries */}
        {alerts.map((alert) => {
          const isSelected = alert.id === selectedAlertId;
          const color = getMarkerColor(alert.predicted_class);

          // Get H3 Hexagon boundary coordinates
          let hexCoords: [number, number][] = [];
          try {
            const hexBoundary = h3.h3ToGeoBoundary(alert.h3_index); // Array of [lat, lon]
            hexCoords = hexBoundary.map(([lat, lon]) => [lat, lon] as [number, number]);
          } catch (e) {
            // Fallback
          }

          return (
            <React.Fragment key={alert.id}>
              {/* H3 Resolution 8 Hex Overlay */}
              {hexCoords.length > 0 && (
                <Polygon
                  positions={hexCoords}
                  pathOptions={{
                    color: color,
                    weight: isSelected ? 2 : 1,
                    opacity: isSelected ? 0.9 : 0.4,
                    fillOpacity: isSelected ? 0.25 : 0.08,
                    fillColor: color,
                  }}
                />
              )}

              {/* Hotspot Pulse Circle Marker */}
              <CircleMarker
                center={[alert.latitude, alert.longitude]}
                radius={isSelected ? 9 : 6}
                pathOptions={{
                  color: "#FFFFFF",
                  weight: isSelected ? 2 : 1,
                  fillColor: color,
                  fillOpacity: 1.0,
                }}
                eventHandlers={{
                  click: () => onSelectAlert(alert.id),
                }}
              >
                <Popup>
                  <div className="font-mono text-xs p-1 leading-tight">
                    <strong style={{ color }} className="uppercase font-bold">
                      {alert.predicted_class.replace("_", " ")}
                    </strong>
                    <br />
                    <span>FRP: {alert.frp} MW</span> | <span>Conf: {(alert.overall_confidence * 100).toFixed(0)}%</span>
                    <br />
                    <span className="text-slate-400">{alert.latitude.toFixed(4)}°, {alert.longitude.toFixed(4)}°</span>
                  </div>
                </Popup>
              </CircleMarker>
            </React.Fragment>
          );
        })}
      </MapContainer>
    </div>
  );
}
