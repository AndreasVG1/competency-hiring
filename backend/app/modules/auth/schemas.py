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
    refresh_token: str
    token_type: str = "bearer"
    user: AuthenticatedUser


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)
    confirm_new_password: str = Field(min_length=1)

    @field_validator("confirm_new_password")
    @classmethod
    def validate_password_confirmation(cls, value: str, info) -> str:
        new_password = info.data.get("new_password")
        if isinstance(new_password, str) and value != new_password:
            raise ValueError("New password confirmation does not match.")
        return value


class DeleteAccountRequest(BaseModel):
    current_password: str = Field(min_length=1)
