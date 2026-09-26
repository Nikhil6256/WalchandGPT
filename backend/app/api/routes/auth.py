"""Auth routes: register, login, logout, profile."""
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, DBDep
from app.core.security import create_access_token, create_refresh_token
from app.models.audit_log import AuditLog
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserProfile
from app.services.user_service import UserService

log = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, db: DBDep):
    """Register a new student/faculty account."""
    user_service = UserService(db)

    if await user_service.get_by_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = await user_service.create_user(
        name=payload.name,
        email=payload.email,
        password=payload.password,
        role=payload.role,
        department=payload.department,
        year=payload.year,
    )

    # Audit log (resilient if DB is offline)
    try:
        db.add(AuditLog(
            user_id=user.id,
            action="register",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=request.client.host if request.client else None,
        ))
        await db.commit()
    except Exception as e:
        log.warning("Audit log write deferred", error=str(e))

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role.value, "email": user.email},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserProfile.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: DBDep):
    """Authenticate with email and password."""
    user_service = UserService(db)
    user = await user_service.authenticate(payload.email, payload.password)

    if not user:
        try:
            db.add(AuditLog(
                action="login_failed",
                details={"email": payload.email},
                ip_address=request.client.host if request.client else None,
            ))
            await db.commit()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    try:
        db.add(AuditLog(
            user_id=user.id,
            action="login_success",
            ip_address=request.client.host if request.client else None,
        ))
        await db.commit()
    except Exception as e:
        log.warning("Audit log write deferred", error=str(e))

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role.value, "email": user.email},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserProfile.model_validate(user),
    )


@router.get("/me", response_model=UserProfile)
async def get_profile(current_user: CurrentUser):
    """Return the authenticated user's profile."""
    return UserProfile.model_validate(current_user)
