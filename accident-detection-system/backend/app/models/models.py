"""
SQLAlchemy ORM models for the accident detection system.
Uses PostGIS geometry types, TimescaleDB hypertables, and pgvector embeddings.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, Enum, Index, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base


# ─────────────────────────── Enums ─────────────────────────────────
class UserRole(str, PyEnum):
    GOVERNMENT = "GOVERNMENT"
    DRIVER     = "DRIVER"
    ADMIN      = "ADMIN"


class AccidentSeverity(str, PyEnum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class AccidentSource(str, PyEnum):
    AI_CAMERA  = "AI_CAMERA"
    USER_REPORT = "USER_REPORT"
    EXTERNAL   = "EXTERNAL"


class IncidentStatus(str, PyEnum):
    DETECTED    = "DETECTED"
    NOTIFIED    = "NOTIFIED"
    RESPONDING  = "RESPONDING"
    RESOLVED    = "RESOLVED"


class NotificationChannel(str, PyEnum):
    SMS          = "SMS"
    CALL         = "CALL"
    PUSH         = "PUSH"
    WHATSAPP     = "WHATSAPP"
    WEBSOCKET    = "WEBSOCKET"


# ─────────────────────────── Models ────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email      = Column(String(255), unique=True, nullable=False, index=True)
    phone      = Column(String(20), unique=True, nullable=True)
    full_name  = Column(String(255), nullable=False)
    role       = Column(Enum(UserRole), nullable=False, default=UserRole.DRIVER)
    hashed_password = Column(String(255), nullable=False)
    fcm_token  = Column(String(512), nullable=True)       # Firebase push token
    is_active  = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Geospatial: last known location
    last_location = Column(Geometry("POINT", srid=4326), nullable=True)
    last_seen_at  = Column(DateTime(timezone=True), nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    accidents_reported = relationship("AccidentEvent", back_populates="reporter", foreign_keys="AccidentEvent.reporter_id")
    notification_logs  = relationship("NotificationLog", back_populates="user")

    __table_args__ = (
        Index("ix_users_last_location", "last_location", postgresql_using="gist"),
    )


class Camera(Base):
    __tablename__ = "cameras"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(255), nullable=False)
    rtsp_url    = Column(String(1024), nullable=False)
    location    = Column(Geometry("POINT", srid=4326), nullable=False)
    address     = Column(Text, nullable=True)
    is_active   = Column(Boolean, default=True)
    added_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    accidents = relationship("AccidentEvent", back_populates="camera")

    __table_args__ = (
        Index("ix_cameras_location", "location", postgresql_using="gist"),
    )


class AccidentEvent(Base):
    """
    Core accident event table.
    TimescaleDB hypertable partitioned by detected_at.
    Includes pgvector embedding for AI similarity search.
    """
    __tablename__ = "accident_events"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detected_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    resolved_at  = Column(DateTime(timezone=True), nullable=True)

    # Location
    location     = Column(Geometry("POINT", srid=4326), nullable=False)
    address      = Column(Text, nullable=True)
    road_name    = Column(String(255), nullable=True)

    # Classification
    severity     = Column(Enum(AccidentSeverity), nullable=False, default=AccidentSeverity.MEDIUM)
    source       = Column(Enum(AccidentSource), nullable=False)
    status       = Column(Enum(IncidentStatus), nullable=False, default=IncidentStatus.DETECTED)

    # AI detection details
    confidence_score = Column(Float, nullable=True)
    ai_model_version = Column(String(50), nullable=True)
    screenshot_url   = Column(String(1024), nullable=True)
    video_clip_url   = Column(String(1024), nullable=True)

    # AI feature embedding (512-dim vector for similarity search)
    # Stored as JSON array for portability (use pgvector extension type in migration)
    embedding    = Column(JSONB, nullable=True)

    # JSONB for flexible extra metadata
    metadata     = Column(JSONB, nullable=True, default=dict)

    # External source info
    external_id  = Column(String(255), nullable=True, unique=True)
    external_src = Column(String(100), nullable=True)

    # Relations
    camera_id    = Column(UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=True)
    reporter_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    camera      = relationship("Camera", back_populates="accidents")
    reporter    = relationship("User", foreign_keys=[reporter_id], back_populates="accidents_reported")
    notifications = relationship("NotificationLog", back_populates="accident")

    __table_args__ = (
        Index("ix_accident_location", "location", postgresql_using="gist"),
        Index("ix_accident_detected_at", "detected_at"),
        Index("ix_accident_severity", "severity"),
        Index("ix_accident_status", "status"),
    )


class NotificationLog(Base):
    """Immutable audit log for every notification dispatched."""
    __tablename__ = "notification_logs"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    accident_id = Column(UUID(as_uuid=True), ForeignKey("accident_events.id"), nullable=False, index=True)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    channel     = Column(Enum(NotificationChannel), nullable=False)
    recipient   = Column(String(512), nullable=False)    # phone/email/token/shop_id
    recipient_type = Column(String(50), nullable=False)  # ambulance|police|driver|shop

    message_body    = Column(Text, nullable=True)
    delivery_status = Column(String(50), nullable=False, default="PENDING")
    provider_message_id = Column(String(255), nullable=True)
    dry_run         = Column(Boolean, default=True)
    sent_at         = Column(DateTime(timezone=True), server_default=func.now())
    error_detail    = Column(Text, nullable=True)

    accident = relationship("AccidentEvent", back_populates="notifications")
    user     = relationship("User", back_populates="notification_logs")

    __table_args__ = (
        Index("ix_notif_log_accident", "accident_id"),
        Index("ix_notif_log_sent_at", "sent_at"),
    )


class AuditLog(Base):
    """Security audit trail for all sensitive operations."""
    __tablename__ = "audit_logs"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), nullable=True)
    action     = Column(String(255), nullable=False, index=True)
    resource   = Column(String(255), nullable=True)
    resource_id = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_data = Column(JSONB, nullable=True)
    status     = Column(String(20), nullable=False, default="SUCCESS")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
