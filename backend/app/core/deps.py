"""
FastAPI dependency injection: database sessions, current user, RBAC.
"""
from typing import Annotated, AsyncGenerator

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole
from app.services.user_service import UserService

log = structlog.get_logger(__name__)

security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Extract and validate the JWT bearer token, returning the authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require the current user to have the ADMIN role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return current_user


async def require_faculty_or_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require the current user to be faculty or admin."""
    if current_user.role not in (UserRole.FACULTY, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faculty or administrator access required",
        )
    return current_user


# Typed aliases for clean dependency injection in route handlers
DBDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
FacultyOrAdminUser = Annotated[User, Depends(require_faculty_or_admin)]
