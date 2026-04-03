from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import CompetencyLevel, RequirementPriority

ExplanationAudience = Literal["seeker", "recruiter"]
ExplanationHighlightKind = Literal["strength"]
ExplanationGapKind = Literal["missing", "insufficient"]


class ExplanationInputValidationError(Exception):
    """Raised when explanation inputs cannot be normalized safely."""

    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ExplanationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str
    status_label: str
    decision_support_notice: str
    must_have_notice: str | None
    no_requirements_notice: str | None


class ExplanationHighlightItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ExplanationHighlightKind = "strength"
    competency_key: str = Field(min_length=1, max_length=255)
    priority: RequirementPriority
    text: str


class ExplanationGapItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ExplanationGapKind
    competency_key: str = Field(min_length=1, max_length=255)
    priority: RequirementPriority
    reason_code: str
    expected_level: CompetencyLevel | None = None
    current_level: CompetencyLevel | None = None
    text: str


class ExplanationRoadmapItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competency_key: str = Field(min_length=1, max_length=255)
    priority: RequirementPriority
    target_level: CompetencyLevel
    estimated_point_gain: float
    text: str


class MatchingExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audience: ExplanationAudience
    algorithm_version: str
    summary: ExplanationSummary
    highlights: list[ExplanationHighlightItem]
    gaps: list[ExplanationGapItem]
    development_roadmap: list[ExplanationRoadmapItem] | None
    transparency_notes: list[str]
