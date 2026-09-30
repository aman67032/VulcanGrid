export type HotspotClass = "controlled_flare" | "industrial_fire" | "forest_fire" | "false_alarm";

export interface ShapFactor {
  feature: string;
  value: number;
  shap_value: number;
  impact: "push_towards" | "push_against";
}

export interface AlertItem {
  id: string;
  hotspot_id?: string;
  firms_id?: string;
  latitude: number;
  longitude: number;
  h3_index: string;
  frp: number;
  brightness: number;
  confidence: number;
  acq_datetime: string;
  predicted_class: HotspotClass;
  class_probs: Record<HotspotClass, number>;
  tier_used: number;
  overall_confidence: number;
  latency_ms: number;
  created_at: string;
  // Detail fields
  shap_explanation?: ShapFactor[];
  feature_vector?: Record<string, number>;
  patch_image_base64?: string;
  wind_speed_ms?: number;
  wind_deg?: number;
}

export interface StatsData {
  total_alerts: number;
  total_hotspots_evaluated: number;
  skipped_hotspots: number;
  pct_cells_skipped: number;
  avg_latency_ms: number;
  class_counts: Record<HotspotClass, number>;
  demo_mode?: boolean;
}

export interface FacilityFeature {
  type: "Feature";
  geometry: {
    type: "Polygon";
    coordinates: number[][][];
  };
  properties: {
    id: string;
    name: string;
    facility_type: "industrial_refinery" | "petrochemical" | "solar_farm" | "steel_plant";
  };
}
