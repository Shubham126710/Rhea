"""
Auth request/response schemas.

Rules.md §3.2: Pydantic models for every API request/response body —
not optional glue code.

PRD Batch B: signup collects ONLY email, display name, password — no
institutional fields, no user-chosen role. Enforced here by simply
not exposing any other field on SignupRequest, so there is no
possible request shape that could smuggle a role/institution through.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=200)

    @field_validator("display_name")
    @classmethod
    def _strip_display_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("display_name must not be blank")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_device: bool = False


class PasswordResetRequestRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=200)


class UserPublic(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
