"""Pydantic schemas for authentication."""
import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.STUDENT
    department: Optional[str] = None
    year: Optional[int] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserProfile(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    department: Optional[str]
    year: Optional[int]
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserProfile
