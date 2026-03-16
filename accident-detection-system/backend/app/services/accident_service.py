"""
Accident orchestration service: ties together AI events, DB writes,
geospatial lookups, notifications, WebSocket broadcasts, and Kafka publishing.
This is the central pipeline on accident detection.
"""
import uuid
from datetime import datetime
from typing import Optional
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID

from app.core.config import settings
from app.core.kafka_client import publish
from app.models.models import AccidentEvent, AccidentSource, AccidentSeverity, IncidentStatus
from app.services.notification_service import NotificationService
from app.services.geospatial_service import GeospatialService
from app.websocket.manager import ws_manager

log = structlog.get_logger(__name__)


class AccidentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notifier = NotificationService(db)
        self.geo = GeospatialService(db)

    async def create_accident(
        self,
        lat: float,
        lon: float,
        severity: str,
        source: str,
        confidence_score: Optional[float] = None,
        camera_id: Optional[uuid.UUID] = None,
        reporter_id: Optional[uuid.UUID] = None,
        screenshot_url: Optional[str] = None,
        ai_model_version: Optional[str] = None,
        metadata: Optional[dict] = None,
        external_id: Optional[str] = None,
        external_src: Optional[str] = None,
    ) -> AccidentEvent:
        """
        Full accident creation pipeline:
        1. Reverse geocode location
        2. Persist accident to DB
        3. Fan-out notifications (parallel)
        4. Broadcast via WebSocket
        5. Publish to Kafka for downstream consumers
        """
        # 1. Geocode
        address = await self.geo.reverse_geocode(lat, lon)

        # 2. Persist
        accident = AccidentEvent(
            location=f"SRID=4326;POINT({lon} {lat})",
            detected_at=datetime.utcnow(),
            severity=AccidentSeverity(severity),
            source=AccidentSource(source),
            status=IncidentStatus.DETECTED,
            confidence_score=confidence_score,
            camera_id=camera_id,
            reporter_id=reporter_id,
            screenshot_url=screenshot_url,
            ai_model_version=ai_model_version,
            address=address,
            metadata=metadata or {},
            external_id=external_id,
            external_src=external_src,
        )
        self.db.add(accident)
        await self.db.flush()   # get accident.id

        log.info(
            "accident.created",
            id=str(accident.id),
            severity=severity,
            source=source,
            lat=lat,
            lon=lon,
        )

        # 3. Fan-out notifications in parallel
        accident_id = accident.id
        nearby_users, nearby_shops = await asyncio.gather(
            self.geo.find_nearby_users(lat, lon),
            self.geo.find_nearby_shops(lat, lon),
        )

        await asyncio.gather(
            self.notifier.notify_emergency_services(
                accident_id, lat, lon, severity, address, screenshot_url
            ),
            self.notifier.notify_nearby_drivers(
                accident_id, lat, lon, severity, address, nearby_users
            ),
            self.notifier.notify_nearby_shops(
                accident_id, lat, lon, severity, address, nearby_shops
            ),
            return_exceptions=True,
        )

        # Update status
        accident.status = IncidentStatus.NOTIFIED
        self.db.add(accident)

        # 4. WebSocket broadcast
        ws_payload = {
            "type": "accident.new",
            "payload": {
                "id": str(accident_id),
                "lat": lat,
                "lon": lon,
                "address": address,
                "severity": severity,
                "source": source,
                "confidence_score": confidence_score,
                "screenshot_url": screenshot_url,
                "detected_at": accident.detected_at.isoformat(),
                "nearby_users_count": len(nearby_users),
                "nearby_shops_count": len(nearby_shops),
            },
        }
        await asyncio.gather(
            ws_manager.broadcast_to_room("gov", ws_payload),
            ws_manager.broadcast_to_room("drivers", ws_payload),
        )

        # 5. Kafka
        await publish(
            settings.KAFKA_ACCIDENT_TOPIC,
            str(accident_id),
            ws_payload["payload"],
        )

        return accident

    async def resolve_accident(self, accident_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(AccidentEvent).where(AccidentEvent.id == accident_id)
        )
        accident = result.scalar_one_or_none()
        if not accident:
            return False
        accident.status = IncidentStatus.RESOLVED
        accident.resolved_at = datetime.utcnow()
        self.db.add(accident)

        await ws_manager.broadcast_all({
            "type": "accident.resolved",
            "payload": {"id": str(accident_id), "resolved_at": accident.resolved_at.isoformat()},
        })
        return True

    async def get_analytics(self) -> dict:
        """Aggregate accident statistics for the government dashboard."""
        total = await self.db.scalar(
            select(func.count()).select_from(AccidentEvent)
        )
        by_severity = await self.db.execute(
            select(AccidentEvent.severity, func.count()).group_by(AccidentEvent.severity)
        )
        by_hour = await self.db.execute(
            text("""
                SELECT date_trunc('hour', detected_at) as hour, COUNT(*) as count
                FROM accident_events
                WHERE detected_at > NOW() - INTERVAL '24 hours'
                GROUP BY hour ORDER BY hour
            """)
        )
        return {
            "total_accidents": total or 0,
            "accidents_by_severity": {row[0]: row[1] for row in by_severity},
            "accidents_by_hour": [{"hour": str(r[0]), "count": r[1]} for r in by_hour],
        }


# avoid circular import at bottom
import asyncio
