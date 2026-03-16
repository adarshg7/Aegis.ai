"""
Pydantic v2 schemas for request validation and response serialization.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ─────────────────────────── Auth ───────────────────────────────────
class UserRegister(BaseModel):
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8)
    role: str = "DRIVER"

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    phone: Optional[str]
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────── Geolocation ────────────────────────────
class Coordinates(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


# ─────────────────────────── Accident Events ────────────────────────
class AccidentCreate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    severity: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    source: str = Field("USER_REPORT", pattern="^(AI_CAMERA|USER_REPORT|EXTERNAL)$")
    address: Optional[str] = None
    road_name: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    screenshot_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AccidentSimulate(BaseModel):
    """Endpoint for testing: simulates an AI-detected accident."""
    latitude: float = Field(28.6139, ge=-90, le=90)   # Delhi as default
    longitude: float = Field(77.2090, ge=-180, le=180)
    severity: str = "HIGH"
    confidence_score: float = 0.92
    camera_id: Optional[uuid.UUID] = None


class AccidentResponse(BaseModel):
    id: uuid.UUID
    detected_at: datetime
    resolved_at: Optional[datetime]
    latitude: float
    longitude: float
    address: Optional[str]
    road_name: Optional[str]
    severity: str
    source: str
    status: str
    confidence_score: Optional[float]
    ai_model_version: Optional[str]
    screenshot_url: Optional[str]
    video_clip_url: Optional[str]
    metadata: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class AccidentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: List[AccidentResponse]


# ─────────────────────────── Camera ─────────────────────────────────
class CameraCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    rtsp_url: str = Field(..., min_length=5)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = None


class CameraResponse(BaseModel):
    id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    address: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────── Notifications ──────────────────────────
class NotificationLogResponse(BaseModel):
    id: uuid.UUID
    accident_id: uuid.UUID
    channel: str
    recipient: str
    recipient_type: str
    delivery_status: str
    dry_run: bool
    sent_at: datetime
    error_detail: Optional[str]

    model_config = {"from_attributes": True}


# ─────────────────────────── WebSocket ──────────────────────────────
class WSMessage(BaseModel):
    """Standardized WebSocket message envelope."""
    type: str            # accident.new | accident.updated | alert.nearby | ping
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────── External Data ──────────────────────────
class ExternalIncident(BaseModel):
    external_id: str
    source: str
    title: str
    latitude: float
    longitude: float
    severity: str = "MEDIUM"
    description: Optional[str] = None
    reported_at: Optional[datetime] = None
    url: Optional[str] = None


# ─────────────────────────── Driver Location ────────────────────────
class UpdateLocation(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


# ─────────────────────────── Analytics ──────────────────────────────
class AnalyticsResponse(BaseModel):
    total_accidents: int
    accidents_by_severity: Dict[str, int]
    accidents_by_hour: List[Dict[str, Any]]
    avg_response_time_minutes: Optional[float]
    hotspots: List[Dict[str, Any]]


# ─────────────────────────── Health ─────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]
