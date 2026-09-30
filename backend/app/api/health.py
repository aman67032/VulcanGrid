from fastapi import APIRouter
from app.config import settings

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "VulcanGrid API",
        "demo_mode": settings.DEMO_MODE,
        "version": "1.0.0"
    }
