"""
Auth API: register, login, refresh, logout, user profile.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    UserRole, hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token, get_current_user
)
from app.models.models import User, AuditLog
from app.schemas.schemas import UserRegister, UserLogin, TokenPair, RefreshRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _audit(db: AsyncSession, action: str, request: Request, user_id=None, status="SUCCESS"):
    log = AuditLog(
        user_id=str(user_id) if user_id else None,
        action=action,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status=status,
    )
    db.add(log)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Only allow DRIVER self-registration; GOVERNMENT accounts must be created by ADMIN
    if body.role.upper() not in ("DRIVER",):
        raise HTTPException(status_code=403, detail="Self-registration only allowed for DRIVER role")

    user = User(
        email=body.email,
        phone=body.phone,
        full_name=body.full_name,
        role=UserRole.DRIVER,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()
    _audit(db, "user.register", request, user.id)
    return user


@router.post("/login", response_model=TokenPair)
async def login(body: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        _audit(db, "user.login.failed", request, status="FAILED")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    role = UserRole(user.role)
    access = create_access_token(str(user.id), role)
    refresh = create_refresh_token(str(user.id), role)
    _audit(db, "user.login", request, user.id)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    role = UserRole(payload["role"])
    access = create_access_token(payload["sub"], role)
    new_refresh = create_refresh_token(payload["sub"], role)
    return TokenPair(access_token=access, refresh_token=new_refresh)


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == current_user["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
