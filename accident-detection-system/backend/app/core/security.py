"""
Security utilities: JWT, bcrypt, RBAC, rate limiting.
"""
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from typing import Optional

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

log = structlog.get_logger(__name__)

# -------------------------------------------------
# Password hashing
# -------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# -------------------------------------------------
# Roles
# -------------------------------------------------
class UserRole(str, Enum):
    GOVERNMENT = "GOVERNMENT"
    DRIVER = "DRIVER"
    ADMIN = "ADMIN"


# -------------------------------------------------
# JWT
# -------------------------------------------------
bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(subject: str, role: UserRole, extra: dict = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": subject,
        "role": role.value,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, role: UserRole) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": subject,
        "role": role.value,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# -------------------------------------------------
# FastAPI dependencies
# -------------------------------------------------
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    return payload


def require_role(*roles: UserRole):
    """Decorator-style dependency to enforce role-based access."""
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role")
        allowed = [r.value for r in roles]
        if user_role not in allowed:
            log.warning(
                "access.denied",
                user=current_user.get("sub"),
                required_roles=allowed,
                user_role=user_role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed}",
            )
        return current_user

    return role_checker


# Convenience dependencies
CurrentUser = Depends(get_current_user)
GovernmentUser = Depends(require_role(UserRole.GOVERNMENT, UserRole.ADMIN))
AdminUser = Depends(require_role(UserRole.ADMIN))
