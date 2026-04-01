from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import JobOfferStatus, RequirementPriority


class RecruiterProfileUpsertRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    contact_name: str = Field(min_length=1, max_length=255)

    @field_validator("company_name", "contact_name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("String should have at least 1 character")
        return normalized


class RecruiterProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    company_name: str
    contact_name: str


class JobOfferCreateRequest(BaseModel):
    occupation_key: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)

    @field_validator("occupation_key", "description")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("String should have at least 1 character")
        return normalized


class JobOfferUpdateRequest(BaseModel):
    occupation_key: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)

    @field_validator("occupation_key", "description")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class JobOfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recruiter_user_id: int
    title: str
    occupation_key: str
    description: str
    status: JobOfferStatus
    created_at: datetime
    updated_at: datetime


class JobOfferRequirementCreateRequest(BaseModel):
    competency_key: str = Field(min_length=1, max_length=255)
    priority: RequirementPriority

    @field_validator("competency_key")
    @classmethod
    def validate_competency_key(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("String should have at least 1 character")
        return normalized


class JobOfferRequirementUpdateRequest(BaseModel):
    priority: RequirementPriority


class JobOfferRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_offer_id: int
    competency_key: str
    priority: RequirementPriority
