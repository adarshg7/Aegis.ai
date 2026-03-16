"""
Core application configuration using Pydantic Settings.
All values are loaded from environment variables / .env file.
"""
from functools import lru_cache
from typing import List
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "AI Accident Detection System"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Database
    DATABASE_URL: str
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "accidentdb"
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_ACCIDENT_TOPIC: str = "accident.events"
    KAFKA_NOTIFICATION_TOPIC: str = "notification.requests"
    KAFKA_EXTERNAL_TOPIC: str = "external.incidents"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Engine
    AI_DETECTION_CONFIDENCE_THRESHOLD: float = 0.65
    AI_DEBOUNCE_SECONDS: int = 10
    AI_FRAME_SAMPLE_RATE: int = 5
    AI_MODEL_PATH: str = "/models/yolov9_accident.pt"
    AI_USE_GPU: bool = False

    # Notifications
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    AMBULANCE_NUMBERS: str = ""
    POLICE_NUMBERS: str = ""
    FIREBASE_SERVER_KEY: str = ""
    FIREBASE_PROJECT_ID: str = ""
    MSG91_API_KEY: str = ""
    MSG91_TEMPLATE_ID: str = ""

    # Maps
    MAPPLS_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    NEARBY_RADIUS_KM: float = 5.0

    # External data
    MAPPLS_TRAFFIC_API_URL: str = "https://apis.mappls.com/advancedmaps/v1"
    ENABLE_EXTERNAL_SCRAPER: bool = True
    EXTERNAL_POLL_INTERVAL_SECONDS: int = 60

    # Mode
    DRY_RUN_NOTIFICATIONS: bool = True
    LOG_LEVEL: str = "INFO"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    @property
    def ambulance_numbers_list(self) -> List[str]:
        return [n.strip() for n in self.AMBULANCE_NUMBERS.split(",") if n.strip()]

    @property
    def police_numbers_list(self) -> List[str]:
        return [n.strip() for n in self.POLICE_NUMBERS.split(",") if n.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
