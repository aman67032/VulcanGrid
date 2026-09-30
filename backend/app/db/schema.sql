-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table 1: Facilities (Industrial & Solar Polygons)
CREATE TABLE IF NOT EXISTS facilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    facility_type VARCHAR(100) NOT NULL, -- industrial_refinery, petrochemical, solar_farm, steel_plant
    geometry GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_facilities_geometry ON facilities USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_facilities_type ON facilities(facility_type);

-- Table 2: Hotspots (Raw Detections & H3 Indexing)
CREATE TABLE IF NOT EXISTS hotspots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    firms_id VARCHAR(100),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    location GEOMETRY(Point, 4326) NOT NULL,
    frp DOUBLE PRECISION NOT NULL,
    brightness DOUBLE PRECISION NOT NULL,
    bright_t31 DOUBLE PRECISION,
    confidence DOUBLE PRECISION,
    acq_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    daynight VARCHAR(1) DEFAULT 'D',
    h3_index VARCHAR(20) NOT NULL,
    skipped BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hotspots_location ON hotspots USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_hotspots_h3 ON hotspots(h3_index);
CREATE INDEX IF NOT EXISTS idx_hotspots_acq ON hotspots(acq_datetime);

-- Table 3: Classified Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hotspot_id UUID REFERENCES hotspots(id) ON DELETE CASCADE,
    firms_id VARCHAR(100),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    location GEOMETRY(Point, 4326) NOT NULL,
    h3_index VARCHAR(20) NOT NULL,
    frp DOUBLE PRECISION NOT NULL,
    brightness DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION,
    acq_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    predicted_class VARCHAR(50) NOT NULL, -- controlled_flare, industrial_fire, forest_fire, false_alarm
    class_probs JSONB NOT NULL,
    tier_used INT NOT NULL, -- 1 or 2
    overall_confidence DOUBLE PRECISION NOT NULL,
    shap_explanation JSONB NOT NULL,
    feature_vector JSONB NOT NULL,
    patch_image_base64 TEXT,
    plume_geometry GEOMETRY(Polygon, 4326),
    wind_speed_ms DOUBLE PRECISION,
    wind_deg DOUBLE PRECISION,
    latency_ms DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_location ON alerts USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_alerts_class ON alerts(predicted_class);
CREATE INDEX IF NOT EXISTS idx_alerts_acq ON alerts(acq_datetime);
CREATE INDEX IF NOT EXISTS idx_alerts_h3 ON alerts(h3_index);
