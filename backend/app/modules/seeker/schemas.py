from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import CompetencyLevel


class SeekerProfileUpsertRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    summary: str | None = None
    location: str | None = Field(default=None, max_length=255)
    occupation_key: str | None = Field(default=None, max_length=255)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("String should have at least 1 character")
        return normalized

    @field_validator("summary", "location", "occupation_key")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class SeekerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    full_name: str
    summary: str | None
    location: str | None
    occupation_key: str | None
    created_at: datetime
    updated_at: datetime


class SeekerCompetencyCreateRequest(BaseModel):
    competency_key: str = Field(min_length=1, max_length=255)
    level: CompetencyLevel

    @field_validator("competency_key")
    @classmethod
    def validate_competency_key(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("String should have at least 1 character")
        return normalized


class SeekerCompetencyUpdateRequest(BaseModel):
    level: CompetencyLevel


class SeekerCompetencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competency_key: str
    level: CompetencyLevel
