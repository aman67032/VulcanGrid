import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").lower() == "true"
    FIRMS_MAP_KEY: str = os.getenv("FIRMS_MAP_KEY", "demo_key")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://vulcan:vulcan_pass@localhost:5432/vulcangrid")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
