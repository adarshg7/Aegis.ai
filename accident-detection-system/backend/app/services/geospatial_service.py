"""
Geospatial service: PostGIS-powered queries for nearby entities.
Finds nearby users, shops (via Mappls/Google), and calculates distances.
"""
import asyncio
from typing import List, Optional
import structlog
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

log = structlog.get_logger(__name__)


class GeospatialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_nearby_users(self, lat: float, lon: float, radius_km: float = None) -> List[dict]:
        """
        Find active drivers within radius using PostGIS ST_DWithin.
        Returns list of user dicts with location and FCM token.
        """
        radius = (radius_km or settings.NEARBY_RADIUS_KM) * 1000  # metres
        sql = text("""
            SELECT
                u.id::text,
                u.full_name,
                u.phone,
                u.fcm_token,
                ST_Distance(
                    u.last_location::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                ) AS distance_m
            FROM users u
            WHERE
                u.is_active = true
                AND u.role = 'DRIVER'
                AND u.fcm_token IS NOT NULL
                AND u.last_location IS NOT NULL
                AND ST_DWithin(
                    u.last_location::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                    :radius
                )
            ORDER BY distance_m ASC
            LIMIT 500
        """)
        result = await self.db.execute(sql, {"lat": lat, "lon": lon, "radius": radius})
        return [dict(row._mapping) for row in result.fetchall()]

    async def find_nearby_shops(self, lat: float, lon: float, radius_km: float = None) -> List[dict]:
        """
        Query Mappls / Google Places API for nearby registered businesses.
        Falls back to Google if Mappls key unavailable.
        """
        radius = (radius_km or settings.NEARBY_RADIUS_KM) * 1000
        shops = []

        # Try Mappls first
        if settings.MAPPLS_API_KEY:
            shops = await self._fetch_mappls_nearby(lat, lon, radius)

        # Fallback: Google Places
        if not shops and settings.GOOGLE_MAPS_API_KEY:
            shops = await self._fetch_google_nearby(lat, lon, radius)

        return shops

    async def _fetch_mappls_nearby(self, lat, lon, radius_m) -> List[dict]:
        url = (
            f"https://atlas.mappls.com/api/places/nearby/json"
            f"?keywords=shop,hospital,pharmacy,police"
            f"&refLocation={lat},{lon}"
            f"&radius={int(radius_m)}"
            f"&access_token={settings.MAPPLS_API_KEY}"
        )
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                data = resp.json()
                results = data.get("suggestedLocations", [])
                return [
                    {
                        "place_id": p.get("placeId", ""),
                        "name": p.get("placeName", "Unknown"),
                        "address": p.get("placeAddress", ""),
                        "phone": p.get("tel", ""),
                        "lat": p.get("latitude"),
                        "lon": p.get("longitude"),
                        "source": "mappls",
                    }
                    for p in results if p.get("tel")
                ]
        except Exception as e:
            log.error("mappls.nearby.failed", error=str(e))
            return []

    async def _fetch_google_nearby(self, lat, lon, radius_m) -> List[dict]:
        url = (
            f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            f"?location={lat},{lon}"
            f"&radius={int(radius_m)}"
            f"&type=store|hospital|police"
            f"&key={settings.GOOGLE_MAPS_API_KEY}"
        )
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                results = resp.json().get("results", [])
                return [
                    {
                        "place_id": p.get("place_id", ""),
                        "name": p.get("name", "Unknown"),
                        "address": p.get("vicinity", ""),
                        "phone": "",       # needs Places Details API call
                        "lat": p["geometry"]["location"]["lat"],
                        "lon": p["geometry"]["location"]["lng"],
                        "source": "google",
                    }
                    for p in results
                ]
        except Exception as e:
            log.error("google.nearby.failed", error=str(e))
            return []

    async def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """Convert GPS coordinates to human-readable address."""
        if settings.MAPPLS_API_KEY:
            try:
                url = (
                    f"https://apis.mappls.com/advancedmaps/v1/{settings.MAPPLS_API_KEY}"
                    f"/rev_geocode?lat={lat}&lng={lon}"
                )
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        results = data.get("results", [{}])
                        return results[0].get("formatted_address") if results else None
            except Exception:
                pass

        if settings.GOOGLE_MAPS_API_KEY:
            try:
                url = (
                    f"https://maps.googleapis.com/maps/api/geocode/json"
                    f"?latlng={lat},{lon}&key={settings.GOOGLE_MAPS_API_KEY}"
                )
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        results = resp.json().get("results", [])
                        return results[0].get("formatted_address") if results else None
            except Exception:
                pass

        return f"{lat:.5f}, {lon:.5f}"
