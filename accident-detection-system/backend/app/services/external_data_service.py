"""
External data ingestion: polls Mappls Traffic API and news feeds
to import accident reports from non-AI sources onto the map.
"""
import asyncio
import hashlib
from datetime import datetime
from typing import List
import structlog
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.models import AccidentEvent, AccidentSource, AccidentSeverity, IncidentStatus

log = structlog.get_logger(__name__)


class ExternalDataService:
    """
    Polls multiple external sources and ingests novel accidents.
    De-duplicates by external_id hash.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_all(self) -> int:
        """Run all sources and return total new incidents ingested."""
        sources = await asyncio.gather(
            self._fetch_mappls_traffic(),
            self._fetch_waze_like_reports(),
            return_exceptions=True,
        )
        incidents = []
        for s in sources:
            if isinstance(s, list):
                incidents.extend(s)

        new_count = 0
        for inc in incidents:
            if await self._is_new(inc.get("external_id", "")):
                await self._save(inc)
                new_count += 1

        if new_count:
            log.info("external.ingested", count=new_count)
        return new_count

    async def _is_new(self, external_id: str) -> bool:
        if not external_id:
            return True
        result = await self.db.execute(
            select(AccidentEvent.id).where(AccidentEvent.external_id == external_id)
        )
        return result.scalar_one_or_none() is None

    async def _save(self, inc: dict):
        lat = inc.get("lat", 0)
        lon = inc.get("lon", 0)
        accident = AccidentEvent(
            location=f"SRID=4326;POINT({lon} {lat})",
            detected_at=inc.get("reported_at") or datetime.utcnow(),
            severity=AccidentSeverity(inc.get("severity", "MEDIUM")),
            source=AccidentSource.EXTERNAL,
            status=IncidentStatus.DETECTED,
            address=inc.get("address"),
            external_id=inc.get("external_id"),
            external_src=inc.get("source"),
            metadata={"title": inc.get("title"), "url": inc.get("url")},
        )
        self.db.add(accident)
        await self.db.flush()

    async def _fetch_mappls_traffic(self) -> List[dict]:
        if not settings.MAPPLS_API_KEY:
            return []
        try:
            url = (
                f"https://apis.mappls.com/advancedmaps/v1/{settings.MAPPLS_API_KEY}"
                f"/trafficalerts?region=IND"
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                data = resp.json()
                incidents = data.get("trafficAlerts", [])
                result = []
                for inc in incidents:
                    lat = inc.get("lat") or inc.get("latitude")
                    lon = inc.get("lon") or inc.get("longitude")
                    if not (lat and lon):
                        continue
                    ext_id = f"mappls_{hashlib.md5(f'{lat}{lon}{inc.get(\"description\",\"\")}'.encode()).hexdigest()}"
                    result.append({
                        "lat": float(lat),
                        "lon": float(lon),
                        "title": inc.get("description", "Traffic Incident"),
                        "severity": "MEDIUM",
                        "source": "mappls_traffic",
                        "external_id": ext_id,
                        "address": inc.get("address"),
                    })
                return result
        except Exception as e:
            log.error("mappls.traffic.fetch.failed", error=str(e))
            return []

    async def _fetch_waze_like_reports(self) -> List[dict]:
        """
        Placeholder for Waze/Here/TomTom incident feed.
        Replace with actual API integration.
        """
        return []
