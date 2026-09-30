import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from geoalchemy2 import Geometry
from app.db.session import Base

class Facility(Base):
    __tablename__ = "facilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    facility_type = Column(String(100), nullable=False)
    geometry = Column(Geometry("POLYGON", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class Hotspot(Base):
    __tablename__ = "hotspots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firms_id = Column(String(100))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    frp = Column(Float, nullable=False)
    brightness = Column(Float, nullable=False)
    bright_t31 = Column(Float)
    confidence = Column(Float)
    acq_datetime = Column(DateTime(timezone=True), nullable=False)
    daynight = Column(String(1), default="D")
    h3_index = Column(String(20), nullable=False)
    skipped = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hotspot_id = Column(UUID(as_uuid=True), ForeignKey("hotspots.id", ondelete="CASCADE"))
    firms_id = Column(String(100))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    h3_index = Column(String(20), nullable=False)
    frp = Column(Float, nullable=False)
    brightness = Column(Float, nullable=False)
    confidence = Column(Float)
    acq_datetime = Column(DateTime(timezone=True), nullable=False)
    predicted_class = Column(String(50), nullable=False)
    class_probs = Column(JSONB, nullable=False)
    tier_used = Column(Integer, nullable=False)
    overall_confidence = Column(Float, nullable=False)
    shap_explanation = Column(JSONB, nullable=False)
    feature_vector = Column(JSONB, nullable=False)
    patch_image_base64 = Column(Text, nullable=True)
    plume_geometry = Column(Geometry("POLYGON", srid=4326), nullable=True)
    wind_speed_ms = Column(Float, nullable=True)
    wind_deg = Column(Float, nullable=True)
    latency_ms = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
