"use client";

import React, { useEffect, useState, useRef } from "react";
import dynamic from "next/dynamic";
import { TopStatsBar } from "../components/TopStatsBar";
import { AlertsSidebar } from "../components/AlertsSidebar";
import { AlertDetailPanel } from "../components/AlertDetailPanel";
import { AlertItem, StatsData } from "../types";

// Dynamically import Leaflet LiveMap component to avoid SSR window errors
const LiveMap = dynamic(() => import("../components/LiveMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-slate-950 flex items-center justify-center font-mono text-slate-500">
      Initializing Spatial Intelligence GIS Canvas...
    </div>
  ),
});

export default function Home() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [selectedClassFilter, setSelectedClassFilter] = useState<string>("ALL");
  const [showPlume, setShowPlume] = useState<boolean>(false);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);

  const wsRef = useRef<WebSocket | null>(null);

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await fetch("/api/sync-firms", { method: "POST" });
      fetchInitialData();
    } catch (err) {
      console.error("Error triggering satellite sync:", err);
    } finally {
      setIsSyncing(false);
    }
  };

  // 1. Fetch initial alerts & stats via REST
  const fetchInitialData = () => {
    fetch("/api/alerts?limit=150")
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setAlerts(data);
          if (data.length > 0 && !selectedAlertId) {
            setSelectedAlertId(data[0].id);
          }
        }
      })
      .catch((err) => console.error("Error fetching initial alerts:", err));

    fetch("/api/stats")
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch((err) => console.error("Error fetching stats:", err));
  };

  useEffect(() => {
    fetchInitialData();
    const statsInterval = setInterval(fetchInitialData, 8000);
    return () => clearInterval(statsInterval);
  }, []);

  // 2. Establish WebSocket connection or graceful REST live polling on serverless
  useEffect(() => {
    const isLocal = typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");
    const customWs = process.env.NEXT_PUBLIC_WS_URL;

    // On cloud serverless deployment without a dedicated WS gateway, use high-frequency REST sync
    if (!customWs && !isLocal) {
      setWsConnected(true);
      return;
    }

    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsHost = customWs || `${wsProtocol}//${window.location.hostname}:8000/ws/alerts`;

    let retryCount = 0;
    const maxRetries = 3;
    let retryTimer: NodeJS.Timeout | null = null;

    const connectWs = () => {
      try {
        const ws = new WebSocket(wsHost);
        wsRef.current = ws;

        ws.onopen = () => {
          setWsConnected(true);
          retryCount = 0;
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.id) {
              setAlerts((prev) => {
                if (prev.some((a) => a.id === data.id)) return prev;
                return [data, ...prev].slice(0, 300);
              });
              fetch("/api/stats")
                .then((res) => res.json())
                .then((s) => setStats(s))
                .catch(() => {});
            }
          } catch (e) {
            // Ignore non-JSON control messages
          }
        };

        ws.onclose = () => {
          if (retryCount < maxRetries) {
            retryCount++;
            setWsConnected(false);
            retryTimer = setTimeout(connectWs, 3000 * retryCount);
          } else {
            // Gracefully fallback to REST sync without console spam
            setWsConnected(true);
          }
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch (err) {
        setWsConnected(true);
      }
    };

    connectWs();

    return () => {
      if (retryTimer) clearTimeout(retryTimer);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Filter alerts by class
  const filteredAlerts = alerts.filter((a) => {
    if (selectedClassFilter === "ALL") return true;
    return a.predicted_class === selectedClassFilter;
  });

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-950 text-slate-100 select-none">
      {/* Top Controls & Metrics Bar */}
      <TopStatsBar
        stats={stats}
        wsConnected={wsConnected}
        selectedClassFilter={selectedClassFilter}
        onSelectClassFilter={setSelectedClassFilter}
        onSync={handleSync}
        isSyncing={isSyncing}
      />

      {/* Main Workspace Grid: Live Map + Sidebar */}
      <div className="relative flex-1 flex overflow-hidden">
        {/* Geospatial Map Canvas */}
        <div className="flex-1 h-full relative">
          <LiveMap
            alerts={filteredAlerts}
            selectedAlertId={selectedAlertId}
            onSelectAlert={setSelectedAlertId}
            showPlume={showPlume}
          />

          {/* Alert Intelligence Detail Panel */}
          <AlertDetailPanel
            alertId={selectedAlertId}
            onClose={() => setSelectedAlertId(null)}
            showPlume={showPlume}
            onTogglePlume={() => setShowPlume((prev) => !prev)}
          />
        </div>

        {/* Right Active Alerts Feed */}
        <AlertsSidebar
          alerts={filteredAlerts}
          selectedAlertId={selectedAlertId}
          onSelectAlert={(id) => {
            setSelectedAlertId(id);
            setShowPlume(false); // Reset plume toggle on select change
          }}
        />
      </div>
    </div>
  );
}
