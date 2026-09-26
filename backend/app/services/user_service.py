"""User service: CRUD + authentication logic."""
import uuid
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole

log = structlog.get_logger(__name__)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        name: str,
        email: str,
        password: str,
        role: UserRole = UserRole.STUDENT,
        department: Optional[str] = None,
        year: Optional[int] = None,
    ) -> User:
        user = User(
            name=name,
            email=email.lower(),
            password_hash=hash_password(password),
            role=role,
            department=department,
            year=year,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        log.info("User created", email=email, role=role.value)
        return user

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        user = await self.get_by_email(email)
        if not user or not user.password_hash:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
