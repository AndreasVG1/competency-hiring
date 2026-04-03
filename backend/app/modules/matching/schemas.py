from pydantic import BaseModel, Field

from app.db.models import CompetencyLevel, RequirementPriority


class MatchingRequirementInput(BaseModel):
    competency_key: str = Field(min_length=1, max_length=255)
    priority: RequirementPriority


class SeekerCompetencyInput(BaseModel):
    competency_key: str = Field(min_length=1, max_length=255)
    level: CompetencyLevel


class MatchingTotals(BaseModel):
    earned_points: float
    max_points: float
    requirements_count: int
    matched_count: int
    insufficient_count: int
    missing_count: int


class MatchingWeightsUsed(BaseModel):
    priority_weights: dict[str, int]
    expected_level_by_priority: dict[str, str]


class MustHaveCoverage(BaseModel):
    total_count: int
    matched_count: int
    insufficient_count: int
    missing_count: int
    coverage_ratio: float


class MatchingBreakdownItem(BaseModel):
    competency_key: str
    priority: RequirementPriority
    expected_level: CompetencyLevel
    seeker_level: CompetencyLevel | None
    status: str
    earned_points: float
    max_points: float
    point_loss: float
    reason_code: str


class MissingCompetencyItem(BaseModel):
    competency_key: str
    priority: RequirementPriority
    reason_code: str


class InsufficientCompetencyItem(BaseModel):
    competency_key: str
    priority: RequirementPriority
    expected_level: CompetencyLevel
    seeker_level: CompetencyLevel
    reason_code: str


class DevelopmentTargetItem(BaseModel):
    competency_key: str
    priority: RequirementPriority
    suggested_target_level: CompetencyLevel
    point_gain_if_reached: float


class MatchingResultPayload(BaseModel):
    algorithm_version: str
    scope: str
    job_offer_id: int
    seeker_user_id: int
    score: float
    status: str
    critical_gap_present: bool
    must_have_coverage: MustHaveCoverage
    totals: MatchingTotals
    weights_used: MatchingWeightsUsed
    breakdown: list[MatchingBreakdownItem]
    missing_competencies: list[MissingCompetencyItem]
    insufficient_competencies: list[InsufficientCompetencyItem]
    development_targets: list[DevelopmentTargetItem]
