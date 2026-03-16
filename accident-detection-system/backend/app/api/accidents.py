"""
Accident events API: CRUD + geospatial queries + simulate endpoint.
"""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text

from app.core.database import get_db
from app.core.security import get_current_user, require_role, UserRole
from app.models.models import AccidentEvent, IncidentStatus
from app.schemas.schemas import (
    AccidentCreate, AccidentResponse, AccidentListResponse,
    AccidentSimulate, AnalyticsResponse
)
from app.services.accident_service import AccidentService

router = APIRouter(prefix="/accidents", tags=["Accidents"])

GOV_OR_ADMIN = Depends(require_role(UserRole.GOVERNMENT, UserRole.ADMIN))


def _to_response(a: AccidentEvent) -> dict:
    if a.location is None:
        lat, lon = 0.0, 0.0
    else:
        from shapely import wkb
        pt = wkb.loads(bytes(a.location.data))
        lat, lon = pt.y, pt.x
    return {
        "id": a.id,
        "detected_at": a.detected_at,
        "resolved_at": a.resolved_at,
        "latitude": lat,
        "longitude": lon,
        "address": a.address,
        "road_name": a.road_name,
        "severity": a.severity.value if hasattr(a.severity, "value") else a.severity,
        "source": a.source.value if hasattr(a.source, "value") else a.source,
        "status": a.status.value if hasattr(a.status, "value") else a.status,
        "confidence_score": a.confidence_score,
        "ai_model_version": a.ai_model_version,
        "screenshot_url": a.screenshot_url,
        "video_clip_url": a.video_clip_url,
        "metadata": a.metadata,
    }


@router.get("", response_model=AccidentListResponse)
async def list_accidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: Optional[str] = None,
    source: Optional[str] = None,
    status: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: Optional[float] = Query(None, le=100),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    query = select(AccidentEvent).order_by(desc(AccidentEvent.detected_at))

    if severity:
        query = query.where(AccidentEvent.severity == severity.upper())
    if source:
        query = query.where(AccidentEvent.source == source.upper())
    if status:
        query = query.where(AccidentEvent.status == status.upper())

    # Geospatial filter
    if lat is not None and lon is not None and radius_km:
        radius_m = radius_km * 1000
        query = query.where(
            text(
                f"ST_DWithin(location::geography, "
                f"ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)::geography, {radius_m})"
            )
        )

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    accidents = result.scalars().all()

    return AccidentListResponse(
        total=total or 0,
        page=page,
        page_size=page_size,
        data=[AccidentResponse(**_to_response(a)) for a in accidents],
    )


@router.get("/{accident_id}", response_model=AccidentResponse)
async def get_accident(
    accident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(select(AccidentEvent).where(AccidentEvent.id == accident_id))
    accident = result.scalar_one_or_none()
    if not accident:
        raise HTTPException(status_code=404, detail="Accident not found")
    return AccidentResponse(**_to_response(accident))


@router.post("", response_model=AccidentResponse, status_code=201)
async def report_accident(
    body: AccidentCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    svc = AccidentService(db)
    accident = await svc.create_accident(
        lat=body.latitude,
        lon=body.longitude,
        severity=body.severity,
        source=body.source,
        confidence_score=body.confidence_score,
        reporter_id=uuid.UUID(current_user["sub"]),
        screenshot_url=body.screenshot_url,
        metadata=body.metadata,
    )
    return AccidentResponse(**_to_response(accident))


@router.post("/simulate", response_model=AccidentResponse, status_code=201)
async def simulate_accident(
    body: AccidentSimulate,
    db: AsyncSession = Depends(get_db),
    gov: dict = GOV_OR_ADMIN,
):
    """Government/Admin-only: Simulate an AI-detected accident for testing."""
    svc = AccidentService(db)
    accident = await svc.create_accident(
        lat=body.latitude,
        lon=body.longitude,
        severity=body.severity,
        source="AI_CAMERA",
        confidence_score=body.confidence_score,
        camera_id=body.camera_id,
        ai_model_version="RT-DETR-YOLOv9-Ensemble-v1.0 (simulation)",
    )
    return AccidentResponse(**_to_response(accident))


@router.patch("/{accident_id}/resolve", response_model=dict)
async def resolve_accident(
    accident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    gov: dict = GOV_OR_ADMIN,
):
    svc = AccidentService(db)
    ok = await svc.resolve_accident(accident_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Accident not found")
    return {"message": "Accident marked as resolved", "id": str(accident_id)}


@router.get("/analytics/summary", response_model=dict)
async def accident_analytics(
    db: AsyncSession = Depends(get_db),
    gov: dict = GOV_OR_ADMIN,
):
    svc = AccidentService(db)
    return await svc.get_analytics()
