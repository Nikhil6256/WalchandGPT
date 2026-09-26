"""User service: CRUD + authentication logic with resilient fallback."""
import uuid
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole

log = structlog.get_logger(__name__)

# In-memory default users for standalone / development mode
FALLBACK_USERS: dict[str, User] = {
    "admin@walchandsangli.ac.in": User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="WalchandGPT Admin",
        email="admin@walchandsangli.ac.in",
        password_hash=hash_password("Admin@1234"),
        role=UserRole.ADMIN,
        is_active=True,
    ),
    "student@walchandsangli.ac.in": User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        name="Demo Student",
        email="student@walchandsangli.ac.in",
        password_hash=hash_password("Student@1234"),
        role=UserRole.STUDENT,
        department="Computer Science and Engineering",
        year=3,
        is_active=True,
    ),
    "faculty@walchandsangli.ac.in": User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        name="Demo Faculty",
        email="faculty@walchandsangli.ac.in",
        password_hash=hash_password("Faculty@1234"),
        role=UserRole.FACULTY,
        department="Computer Science and Engineering",
        is_active=True,
    ),
}


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        try:
            result = await self.db.execute(
                select(User).where(User.id == uuid.UUID(str(user_id)))
            )
            user = result.scalar_one_or_none()
            if user:
                return user
        except Exception:
            pass

        # Check fallback users
        for u in FALLBACK_USERS.values():
            if str(u.id) == str(user_id):
                return u
        return None

    async def get_by_email(self, email: str) -> Optional[User]:
        normalized = email.lower().strip()
        try:
            result = await self.db.execute(
                select(User).where(User.email == normalized)
            )
            user = result.scalar_one_or_none()
            if user:
                return user
        except Exception:
            pass

        return FALLBACK_USERS.get(normalized)

    async def create_user(
        self,
        name: str,
        email: str,
        password: str,
        role: UserRole = UserRole.STUDENT,
        department: Optional[str] = None,
        year: Optional[int] = None,
    ) -> User:
        normalized = email.lower().strip()
        user = User(
            id=uuid.uuid4(),
            name=name,
            email=normalized,
            password_hash=hash_password(password),
            role=role,
            department=department,
            year=year,
            is_active=True,
        )
        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            log.info("User created in DB", email=normalized, role=role.value)
        except Exception as e:
            log.warning("Saving user to in-memory store", email=normalized, error=str(e))

        FALLBACK_USERS[normalized] = user
        return user

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        user = await self.get_by_email(email)
        if not user or not user.password_hash:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
