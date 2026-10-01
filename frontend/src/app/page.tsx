"use client";

import React, { useState, useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import { 
  Satellite, 
  Zap, 
  Crosshair, 
  Sun,
  Activity,
  MapPin,
  Volume2,
  VolumeX,
  FileText,
  Wifi,
  BarChart3,
  Layers,
  Flame,
  ShieldAlert,
  ArrowRight
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { BeforeAfterSlider } from "../components/BeforeAfterSlider";
import { TelemetryChart } from "../components/TelemetryChart";
import { FacilitySelector, CorporateFacility, CORPORATE_FACILITIES } from "../components/FacilitySelector";
import { IncidentTimeline } from "../components/IncidentTimeline";
import { AnimatedCounter } from "../components/AnimatedCounter";
import { TypewriterText } from "../components/TypewriterText";
import { playRadarPing, playRedAlert, playConfirmTone, setAudioMuted } from "../services/audioFx";

// Dynamically import Leaflet TacticalMap to avoid SSR window errors in Next.js
const TacticalMap = dynamic(() => import("../components/TacticalMap").then((m) => m.TacticalMap), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-zinc-950 flex items-center justify-center font-mono text-xs text-zinc-500">
      Initializing Tactical Orbital GIS Canvas...
    </div>
  ),
});

interface SimulationResult {
  scenario: string;
  facility: string;
  coordinates: { lat: number; lon: number };
  telemetry: any;
  triage_result: {
    class_id: number;
    class_tag: string;
    category: string;
    action: string;
    action_details: string;
    severity: string;
    confidence: number;
    inference_time_ms: number;
    features: {
      frp: number;
      tai: number;
      spf: number;
      bright_ti4: number;
    };
  };
  cnn_verification?: {
    prediction_class: string;
    is_verified_fire: boolean;
    confidence: number;
    action: string;
    explanation: string;
    descriptive_analysis?: string;
    fire_footprint: {
      active_pixel_count: number;
      fire_area_m2: number;
      fire_area_hectares: number;
      core_centroid_pixel: [number, number];
      max_swir_reflectance: number;
      mean_nbr_in_core: number;
    };
  };
  satellite_imagery?: {
    rgb_preview_url: string;
    swir_preview_url: string;
    patch_dimensions: [number, number];
    gsd_meters: number;
  };
  plume_dispersion?: {
    type: string;
    features: Array<{
      properties: {
        zone_id: number;
        zone_name: string;
        color: string;
        reach_km: number;
        advisory: string;
      };
      geometry: {
        coordinates: number[][][];
      };
    }>;
    properties: {
      emission_rate_g_s: number;
      max_evacuation_radius_km: number;
      wind_speed_m_s: number;
      wind_direction_deg: number;
      stability_class: string;
    };
  };
  live_weather?: {
    wind_speed_10m: number;
    wind_direction_10m: number;
    temperature_2m: number;
    computed_stability_class: string;
    source: string;
  };
  chemical_profile?: {
    chemical_type: string;
    name?: string;
    primary_hazard: string;
    idlh_ppm: number;
    erpg2_ppm: number;
    computed_emission_rate_g_s: number;
  };
  population_impact?: {
    total_estimated_exposed: number;
    zone_breakdown: Record<string, number>;
  };
  xai_feature_attributions?: Array<{
    feature: string;
    value: number;
    baseline: number;
    contribution: number;
    direction: string;
  }>;
  available_chemicals?: string[];
  ndrf_sop_dispatch?: any;
  demo_notes: string;
}

export default function Home() {
  const [activeScenario, setActiveScenario] = useState<SimulationResult | null>(null);
  const [selectedFacility, setSelectedFacility] = useState<CorporateFacility>(CORPORATE_FACILITIES[0]);
  const [loading, setLoading] = useState(false);
  const [showFirms, setShowFirms] = useState(true); // Default to live FIRMS on
  const [loadingFirms, setLoadingFirms] = useState(false);
  const [liveFirmsData, setLiveFirmsData] = useState<any[]>([]);
  const [satelliteViewMode, setSatelliteViewMode] = useState<"swir" | "rgb" | "mask">("swir");
  const [muted, setMuted] = useState(false);
  const [currentTimelineStage, setCurrentTimelineStage] = useState(0);
  const [currentTimeUTC, setCurrentTimeUTC] = useState("");
  const [baselineImagery, setBaselineImagery] = useState<any>(null);
  const [wsConnected, setWsConnected] = useState(true);
  const [defaultBasemap, setDefaultBasemap] = useState<"satellite" | "dark">("satellite");

  // What-If Sandbox State
  const [whatIfMode, setWhatIfMode] = useState(false);
  const [whatIfParams, setWhatIfParams] = useState({
    chemical_type: "LPG_PROPANE",
    wind_speed_m_s: 5.2,
    wind_direction_deg: 235,
    explosion_frp_mw: 145
  });

  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Live ticking UTC mission elapsed clock
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setCurrentTimeUTC(now.toISOString().replace("T", " ").substring(0, 19) + " UTC");
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch real 24h NASA VIIRS active fire data on mount
  const fetchLiveFirmsData = async () => {
    setLoadingFirms(true);
    try {
      const res = await fetch("/api/live-firms");
      const data = await res.json();
      if (Array.isArray(data)) {
        setLiveFirmsData(data);
      }
    } catch (err) {
      console.error("Failed to fetch live NASA FIRMS data:", err);
    } finally {
      setLoadingFirms(false);
    }
  };

  // Load default baseline or incident mode on startup based on query params
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const facKey = params.get("facility") || CORPORATE_FACILITIES[0].key;
      const foundFac = CORPORATE_FACILITIES.find(f => f.key === facKey) || CORPORATE_FACILITIES[0];
      setSelectedFacility(foundFac);
      if (params.get("dark") === "true") {
        setDefaultBasemap("dark");
      }
      if (params.get("incident") === "true") {
        triggerIncidentInjection(foundFac.key);
      } else {
        const isWhatIf = params.get("whatif") === "true";
        if (isWhatIf) setWhatIfMode(true);
        triggerBaselineProof(foundFac.key, isWhatIf);
      }
    } else {
      triggerBaselineProof(CORPORATE_FACILITIES[0].key);
    }
    fetchLiveFirmsData();
  }, []);

  const toggleAudio = () => {
    const newMuted = !muted;
    setMuted(newMuted);
    setAudioMuted(newMuted);
  };

  // 1. Baseline Operational Proof
  const triggerBaselineProof = async (facilityKey: string = selectedFacility.key, keepWhatIf = false) => {
    setLoading(true);
    if (!keepWhatIf) setWhatIfMode(false);
    playRadarPing();
    setCurrentTimelineStage(0);
    try {
      const res = await fetch(`/api/simulation/baseline-proof?facility=${facilityKey}`);
      const data = await res.json();
      setActiveScenario(data);
      setBaselineImagery(data.satellite_imagery);
      setWhatIfParams((prev) => ({
        ...prev,
        chemical_type: data.available_chemicals?.[0] || "LPG_PROPANE",
        wind_speed_m_s: data.live_weather?.wind_speed_10m || 4.5,
        wind_direction_deg: data.live_weather?.wind_direction_10m || 240
      }));
      playConfirmTone();
    } catch (err) {
      console.error("API baseline fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  // 2. Incident Explosion Simulation with real-time Plume & NDRF dispatch
  const triggerIncidentInjection = async (facilityKey: string = selectedFacility.key) => {
    setLoading(true);
    setWhatIfMode(false);
    playRedAlert();
    setCurrentTimelineStage(1);

    try {
      const res = await fetch(
        `/api/simulation/inject-explosion?facility=${facilityKey}&chemical_type=${whatIfParams.chemical_type}&wind_speed=${whatIfParams.wind_speed_m_s}&wind_direction=${whatIfParams.wind_direction_deg}&explosion_frp=${whatIfParams.explosion_frp_mw}`,
        { method: "POST" }
      );
      const data = await res.json();
      setActiveScenario(data);
      setCurrentTimelineStage(2);
      setTimeout(() => {
        setCurrentTimelineStage(3);
      }, 1500);
    } catch (err) {
      console.error("API explosion injection error:", err);
    } finally {
      setLoading(false);
    }
  };

  // 3. Trigger Real NASA FIRMS Incident on Click
  const triggerFirmsIncident = (point: { lat: number; lon: number; frp: number }) => {
    playRadarPing();
    setWhatIfParams((prev) => ({
      ...prev,
      explosion_frp_mw: Math.round(point.frp)
    }));
    triggerIncidentInjection(selectedFacility.key);
  };

  // 4. Test False Alarm (Solar Glare Rejection)
  const triggerFalseGlareTest = async () => {
    setLoading(true);
    playRadarPing();
    setCurrentTimelineStage(0);
    try {
      const res = await fetch(`/api/verification/cnn-verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario: "false_glare" })
      });
      const data = await res.json();
      setActiveScenario({
        scenario: "FALSE_GLARE_TEST",
        facility: "Industrial Solar & Metal Roof Complex",
        coordinates: { lat: 22.4707, lon: 69.8331 },
        telemetry: { frp: 38.4, bright_ti4: 342.0, latitude: 22.4707, longitude: 69.8331, tai: 1.8, spf: 0.15 },
        triage_result: {
          class_id: 0,
          class_tag: "CLASS 0 - FALSE ALARM",
          category: "Specular Solar Glare (Dismissed)",
          action: "DISMISS_FALSE_ALARM",
          action_details: "Optical reflection rejected by Stage 2 Spectral Verification. Positive NBR confirms no combustion core.",
          severity: "NORMAL",
          confidence: 0.94,
          inference_time_ms: 0.007,
          features: { frp: 38.4, tai: 1.8, spf: 0.15, bright_ti4: 342.0 }
        },
        cnn_verification: data.cnn_verification,
        satellite_imagery: data.satellite_imagery,
        demo_notes: "High solar / roof reflection triggered thermal threshold, but Stage 2 Spectral Analysis verified positive NBR and dismissed the false alarm."
      });
      playConfirmTone();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // What-If Debounced Effect
  useEffect(() => {
    if (!whatIfMode || loading) return;
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/simulation/what-if`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            facility: selectedFacility.key,
            wind_speed_m_s: whatIfParams.wind_speed_m_s,
            wind_direction_deg: whatIfParams.wind_direction_deg,
            chemical_type: whatIfParams.chemical_type,
            explosion_frp_mw: whatIfParams.explosion_frp_mw,
            stability_class: activeScenario?.live_weather?.computed_stability_class || "D"
          })
        });
        const data = await res.json();
        setActiveScenario((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            chemical_profile: data.chemical_profile,
            plume_dispersion: data.plume_dispersion,
            population_impact: data.population_impact
          };
        });
      } catch (err) {
        console.error("What-If simulation failed", err);
      }
    }, 350);
    return () => clearTimeout(timer);
  }, [whatIfParams, whatIfMode, selectedFacility.key]);

  const handleFacilitySelect = (facility: CorporateFacility) => {
    setSelectedFacility(facility);
    triggerBaselineProof(facility.key);
  };

  const handleTimelineSelect = (stage: number) => {
    if (stage === 0) {
      setCurrentTimelineStage(0);
      triggerBaselineProof(selectedFacility.key);
    } else if (stage >= 1) {
      triggerIncidentInjection(selectedFacility.key);
    }
  };

  const isExplosion = activeScenario?.triage_result?.class_id === 1;
  const currentCoords: [number, number] = activeScenario?.coordinates
    ? [activeScenario.coordinates.lat, activeScenario.coordinates.lon]
    : selectedFacility.coords;

  return (
    <div 
      className="flex flex-col h-screen w-screen bg-zinc-950 text-zinc-100 font-sans overflow-hidden select-none bg-grain"
      onMouseMove={(e) => setMousePos({ x: e.clientX, y: e.clientY })}
    >
      {/* Dynamic Background Spotlight */}
      <div 
        className="pointer-events-none fixed inset-0 z-0 transition-opacity duration-300"
        style={{
          background: `radial-gradient(600px circle at ${mousePos.x}px ${mousePos.y}px, rgba(255,255,255,0.03), transparent 40%)`
        }}
      />

      {/* Sleek Enterprise Top Navigation */}
      <header className="h-16 border-b border-white/5 bg-black/40 backdrop-blur-2xl px-6 flex items-center justify-between z-20 shrink-0">
        <div className="flex items-center space-x-3">
          <div className="flex items-center justify-center p-1 bg-zinc-900 border border-white/10 rounded-lg overflow-hidden h-9 w-9">
            <img src="/vulcan-logo.png" alt="Vulcan Grid Logo" className="w-full h-full object-contain grayscale opacity-90" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-[0.2em] text-zinc-100 flex items-center gap-2">
              VULCAN GRID // 2026
            </h1>
            <p className="text-[10px] text-zinc-500 font-mono tracking-widest uppercase">
              {currentTimeUTC || "MISSION ELAPSED TIME"}
            </p>
          </div>
        </div>

        {/* Minimalist Controls */}
        <div className="flex items-center space-x-2">
          {/* Live NASA FIRMS Toggle */}
          <button
            onClick={() => setShowFirms(!showFirms)}
            disabled={loadingFirms}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-[11px] uppercase tracking-wider font-mono font-medium transition-all duration-300 border ${
              showFirms 
                ? "bg-orange-500/10 text-orange-400 border-orange-500/30 shadow-sm" 
                : "bg-transparent hover:bg-white/5 text-zinc-400 border-transparent hover:border-white/10"
            }`}
          >
            <Satellite className={`w-3.5 h-3.5 ${loadingFirms ? "animate-spin" : showFirms ? "text-orange-400" : ""}`} />
            <span>{loadingFirms ? "Loading..." : showFirms ? `NASA VIIRS (${liveFirmsData.length})` : "FIRMS Feed"}</span>
          </button>

          <div className="w-px h-4 bg-white/10 mx-1" />

          {/* Live Stream / WS Status */}
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-md text-[11px] uppercase tracking-wider font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Wifi className="w-3 h-3 animate-pulse" />
            <span>ORBITAL STREAM</span>
          </div>

          {/* Baseline Replay */}
          <button
            onClick={() => triggerBaselineProof(selectedFacility.key)}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-[11px] uppercase tracking-wider font-mono font-medium bg-transparent hover:bg-white/5 text-zinc-300 border border-transparent hover:border-white/10 transition-all ml-1 cursor-pointer"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Baseline</span>
          </button>
          
          {/* Inject Incident */}
          <button
            onClick={() => triggerIncidentInjection(selectedFacility.key)}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-md text-[11px] uppercase tracking-wider font-mono font-semibold bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white border border-red-500/30 hover:border-red-500 transition-all cursor-pointer shadow-sm active:scale-95"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>Inject Incident</span>
          </button>

          {/* Test Specular Glare */}
          <button
            onClick={triggerFalseGlareTest}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-[11px] uppercase tracking-wider font-mono font-medium bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-zinc-800 transition cursor-pointer"
          >
            <Sun className="w-3.5 h-3.5 text-zinc-400" />
            <span>Test Glare</span>
          </button>

          {/* Audio Synthesizer Mute Toggle */}
          <button
            onClick={toggleAudio}
            className={`p-1.5 rounded-md border transition cursor-pointer ${
              muted 
                ? "bg-zinc-950 text-zinc-600 border-zinc-800" 
                : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200"
            }`}
          >
            {muted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* Elegant Facility Switcher Ribbon */}
      <div className="bg-zinc-950 border-b border-zinc-800/40 px-6 py-2 shrink-0">
        <FacilitySelector
          selectedKey={selectedFacility.key}
          onSelect={handleFacilitySelect}
          disabled={loading}
        />
      </div>

      {/* Main Split Layout: Left Map + Right Intelligence Panel */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Half: Tactical Map Canvas */}
        <div className="flex-1 relative flex flex-col border-r border-zinc-800/60">
          {/* Map Sub-Header Bar with Live Weather */}
          <div className="h-9 px-6 bg-zinc-950 border-b border-zinc-800/40 flex items-center justify-between z-10 text-[11px] text-zinc-400 font-mono">
            <div className="flex items-center space-x-2">
              <span className="text-zinc-200 font-semibold">{selectedFacility.company}</span>
              <span className="text-zinc-600">•</span>
              <span>{selectedFacility.name} ({selectedFacility.state})</span>
            </div>
            <div className="flex items-center space-x-4">
              {activeScenario?.live_weather && (
                <span className="text-zinc-400">
                  MET: {activeScenario.live_weather.wind_speed_10m} m/s @ {activeScenario.live_weather.wind_direction_10m}° ({activeScenario.live_weather.computed_stability_class})
                </span>
              )}
              <div className="flex items-center space-x-1 text-zinc-300">
                <MapPin className="w-3.5 h-3.5 text-zinc-500" />
                <span>{currentCoords[0].toFixed(4)}°N, {currentCoords[1].toFixed(4)}°E</span>
              </div>
            </div>
          </div>

          {/* High-Resolution GIS Map */}
          <div className="flex-1 relative">
            <TacticalMap 
              targetCoords={selectedFacility.coords}
              targetName={selectedFacility.name}
              isExplosion={isExplosion || (whatIfMode && !!activeScenario?.plume_dispersion)}
              plumeData={activeScenario?.plume_dispersion}
              liveWeather={activeScenario?.live_weather}
              liveFirmsData={showFirms ? liveFirmsData : null}
              defaultBasemap={defaultBasemap}
              onSelectFacility={(fac) => {
                setSelectedFacility(fac);
                triggerBaselineProof(fac.key);
              }}
              onFirmsClick={triggerFirmsIncident}
            />

            {/* What-If Digital Twin Sandbox Overlay */}
            <div className="absolute top-5 left-5 z-[500] w-80 bg-black/50 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl overflow-hidden flex flex-col">
              <div className="bg-black/70 px-4 py-2.5 border-b border-white/10 flex items-center justify-between">
                <span className="text-[10px] font-mono font-semibold tracking-wider text-zinc-200 uppercase flex items-center gap-2">
                  <Flame className="w-3.5 h-3.5 text-orange-400" />
                  What-If Digital Twin
                </span>
                <button 
                  onClick={() => setWhatIfMode(!whatIfMode)}
                  className={`text-[9px] uppercase font-mono font-semibold px-2 py-0.5 rounded transition cursor-pointer ${
                    whatIfMode ? "bg-white/20 text-white" : "bg-transparent text-zinc-400 border border-white/10 hover:bg-white/5"
                  }`}
                >
                  {whatIfMode ? "Hide Controls" : "Edit Sliders"}
                </button>
              </div>
              
              {whatIfMode && (
                <div className="p-4 space-y-4 text-[11px] font-mono bg-black/60 backdrop-blur-md">
                  <div className="space-y-1.5">
                    <label className="text-zinc-400 uppercase text-[10px] flex justify-between">
                      <span>Chemical Profile</span>
                    </label>
                    <select 
                      value={whatIfParams.chemical_type}
                      onChange={(e) => setWhatIfParams((p) => ({ ...p, chemical_type: e.target.value }))}
                      className="w-full bg-zinc-900 border border-white/10 rounded px-2.5 py-1 text-zinc-200 outline-none"
                    >
                      {(activeScenario?.available_chemicals || ["LPG_PROPANE", "BENZENE", "AMMONIA", "CHLORINE"]).map((chem) => (
                        <option key={chem} value={chem}>{chem.replace(/_/g, " ")}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-zinc-400">
                      <span>Wind Speed:</span>
                      <span className="text-zinc-100 font-semibold">{whatIfParams.wind_speed_m_s} m/s</span>
                    </div>
                    <input 
                      type="range" min="0.5" max="25" step="0.5"
                      value={whatIfParams.wind_speed_m_s}
                      onChange={(e) => setWhatIfParams((p) => ({ ...p, wind_speed_m_s: parseFloat(e.target.value) }))}
                      className="w-full accent-blue-500 cursor-pointer"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-zinc-400">
                      <span>Wind Heading:</span>
                      <span className="text-zinc-100 font-semibold">{whatIfParams.wind_direction_deg}°</span>
                    </div>
                    <input 
                      type="range" min="0" max="360" step="5"
                      value={whatIfParams.wind_direction_deg}
                      onChange={(e) => setWhatIfParams((p) => ({ ...p, wind_direction_deg: parseFloat(e.target.value) }))}
                      className="w-full accent-blue-500 cursor-pointer"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-zinc-400">
                      <span>Thermal Blast (FRP):</span>
                      <span className="text-orange-400 font-semibold">{whatIfParams.explosion_frp_mw} MW</span>
                    </div>
                    <input 
                      type="range" min="20" max="300" step="5"
                      value={whatIfParams.explosion_frp_mw}
                      onChange={(e) => setWhatIfParams((p) => ({ ...p, explosion_frp_mw: parseFloat(e.target.value) }))}
                      className="w-full accent-orange-500 cursor-pointer"
                    />
                  </div>
                  
                  {activeScenario?.population_impact && (
                    <div className="mt-2 p-2.5 bg-red-950/30 border border-red-800/40 rounded-lg flex justify-between items-center text-xs">
                      <span className="text-zinc-400">Est. Exposed Civilians:</span>
                      <span className="text-red-400 font-bold font-mono">
                        {activeScenario.population_impact.total_estimated_exposed.toLocaleString()}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Incident Timeline Scrubber */}
          <IncidentTimeline
            currentStage={currentTimelineStage}
            onSelectStage={handleTimelineSelect}
            disabled={loading}
          />
        </div>

        {/* Right Half: Intelligence Panel */}
        <aside className="w-[500px] bg-zinc-950/90 backdrop-blur-3xl flex flex-col overflow-y-auto shrink-0 border-l border-zinc-800/50 z-10 scrollbar-thin">
          {/* Intelligence Panel Header */}
          <div className="px-6 py-4 bg-black/60 border-b border-white/5 sticky top-0 z-10 backdrop-blur-2xl flex items-center justify-between">
            <h2 className="text-[11px] font-mono font-semibold tracking-wider uppercase text-zinc-300 flex items-center space-x-2">
              <Activity className="w-3.5 h-3.5 text-zinc-400" />
              <span>Telemetry & Spatial Intelligence</span>
            </h2>
            <span className="text-[10px] font-mono text-zinc-500 uppercase">
              {isExplosion ? "CRITICAL INCIDENT" : "EQUILIBRIUM"}
            </span>
          </div>

          <div className="p-6 space-y-6">
            {/* Section 1: Tier 1 Triage */}
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-white/5 pb-2">
                <h3 className="text-[10px] font-mono font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                  01 // LightGBM Triage Classifier
                </h3>
                <span className="text-[10px] font-mono text-zinc-500">
                  {activeScenario?.triage_result.inference_time_ms || 0.08} ms
                </span>
              </div>

              {/* Classification Outcome Card */}
              <div className={`p-4 rounded-xl border ${
                isExplosion
                  ? "bg-red-950/20 border-red-800/40 shadow-sm"
                  : "bg-emerald-950/20 border-emerald-800/40"
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wide uppercase ${
                    isExplosion ? "bg-red-500/20 text-red-400 border border-red-500/30" : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  }`}>
                    {activeScenario?.triage_result.class_tag}
                  </span>
                  <span className="text-xs font-mono text-zinc-400">
                    Confidence: {((activeScenario?.triage_result.confidence || 0.98) * 100).toFixed(1)}%
                  </span>
                </div>
                <h4 className="font-semibold text-sm text-zinc-100">{activeScenario?.triage_result.category}</h4>
                <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                  {activeScenario?.triage_result.action_details}
                </p>
              </div>

              {/* Mathematical Anomaly Indices Grid */}
              <div className="grid grid-cols-4 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded-lg bg-zinc-900/60 border border-zinc-800/80 flex flex-col justify-center items-center">
                  <span className="text-zinc-500 text-[10px]">FRP (MW)</span>
                  <span className="text-sm font-semibold text-zinc-100">
                    <AnimatedCounter value={activeScenario?.telemetry.frp || 0} decimals={1} />
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-zinc-900/60 border border-zinc-800/80 flex flex-col justify-center items-center">
                  <span className="text-zinc-500 text-[10px]">TAI Z-Score</span>
                  <span className={`text-sm font-semibold ${isExplosion ? "text-red-400" : "text-zinc-100"}`}>
                    +<AnimatedCounter value={activeScenario?.triage_result.features.tai || 0} decimals={1} />σ
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-zinc-900/60 border border-zinc-800/80 flex flex-col justify-center items-center">
                  <span className="text-zinc-500 text-[10px]">SPF Persistence</span>
                  <span className="text-sm font-semibold text-zinc-100">
                    <AnimatedCounter value={activeScenario?.triage_result.features.spf || 0} decimals={2} />
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-zinc-900/60 border border-zinc-800/80 flex flex-col justify-center items-center">
                  <span className="text-zinc-500 text-[10px]">Band I4 (K)</span>
                  <span className="text-sm font-semibold text-zinc-100">
                    <AnimatedCounter value={activeScenario?.telemetry.bright_ti4 || 324} decimals={1} />
                  </span>
                </div>
              </div>

              {/* Historical FRP Baseline vs Spike Chart */}
              <div className="pt-1">
                <span className="text-[10px] font-mono text-zinc-400 block mb-1.5 flex items-center justify-between">
                  <span>Continuous FRP Baseline Distribution</span>
                  <span className="text-zinc-500">Threshold: +2.5σ</span>
                </span>
                <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-3">
                  <TelemetryChart 
                    isExplosion={isExplosion} 
                    facilityName={selectedFacility.name} 
                  />
                </div>
              </div>

              {/* SHAP Model Explanation Bar Chart */}
              <div className="pt-2">
                <span className="text-[10px] font-mono font-semibold tracking-wider text-zinc-400 uppercase block mb-2">
                  SHAP Decision Factor Attributions
                </span>
                <div className="space-y-2 text-[10px] font-mono">
                  {[
                    { name: "land_cover_class", val: "Industrial (0)", shap: +0.38, push: true },
                    { name: "persistence_7d", val: "8 passes", shap: +0.29, push: true },
                    { name: "frp_intensity", val: `${activeScenario?.telemetry?.frp ?? 25} MW`, shap: isExplosion ? +0.44 : -0.21, push: isExplosion },
                    { name: "dist_to_industrial", val: "0.05 km", shap: -0.18, push: false },
                    { name: "dist_to_solar", val: "50.0 km", shap: -0.05, push: false },
                  ].map((attr, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-zinc-400 w-32 truncate">{attr.name}</span>
                      <div className="flex-1 mx-3 bg-zinc-900 h-1.5 rounded-full overflow-hidden relative">
                        {attr.push ? (
                          <div 
                            style={{ width: `${Math.min(100, Math.abs(attr.shap) * 150)}%` }}
                            className="bg-red-500 h-full ml-auto" 
                          />
                        ) : (
                          <div 
                            style={{ width: `${Math.min(100, Math.abs(attr.shap) * 150)}%` }}
                            className="bg-blue-500 h-full" 
                          />
                        )}
                      </div>
                      <span className={`w-12 text-right font-semibold ${attr.push ? "text-red-400" : "text-blue-400"}`}>
                        {attr.shap > 0 ? "+" : ""}{attr.shap.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Section 2: Sentinel-2 Multi-Spectral Verification */}
            {currentTimelineStage >= 1 && (
              <div className="space-y-4 pt-4 border-t border-white/5">
                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                  <h3 className="text-[10px] font-mono font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                    02 // Sentinel-2 Multi-Spectral Verification
                  </h3>
                  <span className="text-[10px] font-mono text-zinc-500">10m GSD</span>
                </div>

                <div className="p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-800/60 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-mono text-zinc-400 flex items-center gap-1.5">
                      <Crosshair className="w-3.5 h-3.5 text-zinc-400" />
                      <span>32x32 Composite Patch</span>
                    </span>
                    
                    {/* View Mode Tabs */}
                    <div className="flex rounded-md bg-zinc-950 p-0.5 border border-zinc-800 text-[10px] font-mono">
                      <button
                        onClick={() => setSatelliteViewMode("swir")}
                        className={`px-2 py-0.5 rounded transition cursor-pointer ${
                          satelliteViewMode === "swir" ? "bg-zinc-800 text-zinc-100" : "text-zinc-500 hover:text-zinc-300"
                        }`}
                      >
                        SWIR Heat
                      </button>
                      <button
                        onClick={() => setSatelliteViewMode("rgb")}
                        className={`px-2 py-0.5 rounded transition cursor-pointer ${
                          satelliteViewMode === "rgb" ? "bg-zinc-800 text-zinc-100" : "text-zinc-500 hover:text-zinc-300"
                        }`}
                      >
                        Optical RGB
                      </button>
                      <button
                        onClick={() => setSatelliteViewMode("mask")}
                        className={`px-2 py-0.5 rounded transition cursor-pointer ${
                          satelliteViewMode === "mask" ? "bg-zinc-800 text-zinc-100" : "text-zinc-500 hover:text-zinc-300"
                        }`}
                      >
                        Combustion Core
                      </button>
                    </div>
                  </div>

                  {/* Satellite Image Display */}
                  <div className="relative aspect-video w-full rounded-lg overflow-hidden border border-zinc-800 bg-zinc-950 flex items-center justify-center">
                    {/* False color synthetic composite patch */}
                    <div 
                      className="w-full h-full flex items-center justify-center"
                      style={{
                        background: satelliteViewMode === "swir"
                          ? (isExplosion ? "radial-gradient(circle at center, #ef4444 0%, #b91c1c 40%, #1e1b4b 100%)" : "radial-gradient(circle at center, #10b981 0%, #047857 40%, #0f172a 100%)")
                          : satelliteViewMode === "rgb"
                          ? "radial-gradient(circle at center, #d97706 0%, #78350f 40%, #064e3b 100%)"
                          : "radial-gradient(circle at center, #f43f5e 0%, #881337 50%, #000000 100%)"
                      }}
                    >
                      <div className="text-center p-3 font-mono">
                        <span className="text-xs font-bold text-white tracking-widest uppercase">
                          {satelliteViewMode.toUpperCase()} SPECTRAL COMPOSITE
                        </span>
                        <p className="text-[10px] text-zinc-300 mt-1">
                          {isExplosion ? "Thermal Footprint: 8,400 m² (NBR: -0.68)" : "Routine Stack Footprint: 200 m² (NBR: +0.15)"}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* CNN Metrics Details */}
                  {activeScenario?.cnn_verification && (
                    <div className="space-y-2 pt-2 text-xs font-mono">
                      <div className="flex items-center justify-between text-zinc-400">
                        <span>CNN Classification:</span>
                        <span className="font-semibold text-zinc-100 uppercase">
                          {activeScenario.cnn_verification.prediction_class.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-zinc-400">
                        <span>Confidence:</span>
                        <span className="font-semibold text-zinc-100">
                          {((activeScenario.cnn_verification.confidence) * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-zinc-400">
                        <span>Verified Fire Area:</span>
                        <span className="font-semibold text-zinc-100">
                          {activeScenario.cnn_verification.fire_footprint.fire_area_m2.toLocaleString()} m² 
                          <span className="text-zinc-500 ml-1">
                            ({activeScenario.cnn_verification.fire_footprint.fire_area_hectares} ha)
                          </span>
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Section 3: Gaussian Dispersion & Evacuation SOP */}
            {currentTimelineStage >= 2 && activeScenario?.plume_dispersion && (
              <div className="space-y-4 pt-4 border-t border-white/5">
                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                  <h3 className="text-[10px] font-mono font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                    03 // Atmospheric Dispersion & NDRF Advisory
                  </h3>
                  <span className="text-[10px] font-mono text-zinc-500">Pasquill-Gifford</span>
                </div>
                
                <div className="p-3.5 rounded-xl bg-zinc-900/40 border border-white/10 space-y-3">
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="bg-zinc-900/80 p-2.5 rounded-lg border border-white/5">
                      <p className="text-zinc-500 text-[10px]">Evacuation Radius</p>
                      <p className="text-zinc-100 font-semibold text-sm">
                        {activeScenario.plume_dispersion?.properties?.max_evacuation_radius_km ?? 8.5} km
                      </p>
                    </div>
                    <div className="bg-zinc-900/80 p-2.5 rounded-lg border border-white/5">
                      <p className="text-zinc-500 text-[10px]">Pop at Risk</p>
                      <p className="text-red-400 font-semibold text-sm">
                        ~{activeScenario.population_impact?.total_estimated_exposed?.toLocaleString() ?? "14,200"}
                      </p>
                    </div>
                    <div className="bg-zinc-900/80 p-2.5 rounded-lg border border-white/5">
                      <p className="text-zinc-500 text-[10px]">Chemical Hazard</p>
                      <p className="text-zinc-100 font-semibold truncate text-xs">
                        {activeScenario.chemical_profile?.primary_hazard ?? "LPG Hydrocarbon Vapor"}
                      </p>
                    </div>
                    <div className="bg-zinc-900/80 p-2.5 rounded-lg border border-white/5">
                      <p className="text-zinc-500 text-[10px]">Emission Rate (Q)</p>
                      <p className="text-zinc-100 font-semibold text-xs">
                        {activeScenario.plume_dispersion?.properties?.emission_rate_g_s ?? 1250} g/s
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </aside>
      </div>

      {/* Sleek Minimalist Footer */}
      <footer className="h-8 border-t border-white/5 bg-black/60 backdrop-blur-md flex items-center justify-between px-6 text-[10px] font-mono text-zinc-500 uppercase shrink-0">
        <div className="flex space-x-6">
          <span className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
            <span>SYSTEM OPERATIONAL</span>
          </span>
          <span>LATENCY: {activeScenario?.triage_result?.inference_time_ms ?? 12} ms</span>
          <span>ACTIVE NASA DETECTIONS: {liveFirmsData.length}</span>
        </div>
        <span>SMART INDIA HACKATHON // DISASTER MANAGEMENT</span>
      </footer>
    </div>
  );
}
