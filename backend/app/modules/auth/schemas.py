from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import UserRole


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)
    role: UserRole

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_email = value.strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise ValueError("value is not a valid email address")
        return normalized_email


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_email = value.strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise ValueError("value is not a valid email address")
        return normalized_email


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: UserRole
    created_at: datetime


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthenticatedUser
