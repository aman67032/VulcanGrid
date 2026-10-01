from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import health, alerts, websocket, tactical

app = FastAPI(
    title="VulcanGrid Thermal Hotspot Classifier API",
    description="AI dual-tier classification & spatial intelligence engine for thermal satellite hotspots",
    version="1.0.0"
)

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if "https://frontend-three-ruddy-fpb7kkoydz.vercel.app" not in origins:
    origins.append("https://frontend-three-ruddy-fpb7kkoydz.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(alerts.router)
app.include_router(websocket.router)
app.include_router(tactical.router)
app.include_router(tactical.router, prefix="/api")

@app.get("/")
def root():
    return {
        "system": "VulcanGrid",
        "status": "online",
        "demo_mode": settings.DEMO_MODE,
        "docs": "/docs"
    }
