from dataclasses import dataclass

from app.db.models import CompetencyLevel, RequirementPriority
from app.modules.matching.schemas import (
    DevelopmentTargetItem,
    InsufficientCompetencyItem,
    MatchingBreakdownItem,
    MatchingRequirementInput,
    MatchingResultPayload,
    MatchingTotals,
    MatchingWeightsUsed,
    MissingCompetencyItem,
    MustHaveCoverage,
    SeekerCompetencyInput,
)

ALGORITHM_VERSION = "v2_exact_priority_level_dual_signal"
PRIVATE_PREVIEW_SCOPE = "private_preview"

# Phase 3 MVP normative mappings:
# - priority drives maximum points
# - level strings map to deterministic numeric ratios
# - expected level is a global rule per requirement priority
PRIORITY_WEIGHTS = {
    RequirementPriority.MUST_HAVE: 5,
    RequirementPriority.IMPORTANT: 3,
    RequirementPriority.NICE_TO_HAVE: 1,
}
LEVEL_NUMERIC = {
    CompetencyLevel.BEGINNER: 1,
    CompetencyLevel.INTERMEDIATE: 2,
    CompetencyLevel.ADVANCED: 3,
}
EXPECTED_LEVEL_BY_PRIORITY = {
    RequirementPriority.MUST_HAVE: CompetencyLevel.INTERMEDIATE,
    RequirementPriority.IMPORTANT: CompetencyLevel.INTERMEDIATE,
    RequirementPriority.NICE_TO_HAVE: CompetencyLevel.BEGINNER,
}
PRIORITY_SORT_RANK = {
    RequirementPriority.MUST_HAVE: 0,
    RequirementPriority.IMPORTANT: 1,
    RequirementPriority.NICE_TO_HAVE: 2,
}


class MatchingInputValidationError(Exception):
    """Raised when matching input fails pre-evaluation validation."""

    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class _EvaluatedRequirement:
    """Normalized per-requirement result reused across all output sections."""

    competency_key: str
    priority: RequirementPriority
    expected_level: CompetencyLevel
    seeker_level: CompetencyLevel | None
    status: str
    earned_points: float
    max_points: float
    point_loss: float
    reason_code: str


def _sort_key(row: _EvaluatedRequirement) -> tuple[int, float, str]:
    # Stable explanation ordering required by the Phase 3 contract:
    # 1) priority severity, 2) point loss descending, 3) competency key asc.
    return (
        PRIORITY_SORT_RANK[row.priority],
        -row.point_loss,
        row.competency_key,
    )


def _raise_input_error(*, code: str, message: str) -> None:
    raise MatchingInputValidationError(code=code, message=message)


def _validate_competency_key(
    *,
    competency_key: str,
    source: str,
    index: int,
) -> None:
    if competency_key.strip():
        return
    _raise_input_error(
        code="blank_competency_key",
        message=f"{source}[{index}].competency_key must not be blank or whitespace-only.",
    )


def _validate_requirements(requirements: list[MatchingRequirementInput]) -> None:
    seen_keys: set[str] = set()

    for index, requirement in enumerate(requirements):
        _validate_competency_key(
            competency_key=requirement.competency_key,
            source="requirements",
            index=index,
        )

        if requirement.priority not in PRIORITY_WEIGHTS:
            unsupported_value = getattr(
                requirement.priority,
                "value",
                requirement.priority,
            )
            _raise_input_error(
                code="unknown_requirement_priority",
                message=(
                    f"requirements[{index}].priority has unsupported value: "
                    f"{unsupported_value!r}."
                ),
            )

        if requirement.competency_key in seen_keys:
            _raise_input_error(
                code="duplicate_requirement_competency_key",
                message=(
                    f"Duplicate requirement competency_key: "
                    f"{requirement.competency_key!r}."
                ),
            )
        seen_keys.add(requirement.competency_key)


def _validate_seeker_competencies(
    seeker_competencies: list[SeekerCompetencyInput],
) -> None:
    seen_keys: set[str] = set()

    for index, competency in enumerate(seeker_competencies):
        _validate_competency_key(
            competency_key=competency.competency_key,
            source="seeker_competencies",
            index=index,
        )

        if competency.level not in LEVEL_NUMERIC:
            unsupported_value = getattr(competency.level, "value", competency.level)
            _raise_input_error(
                code="unknown_competency_level",
                message=(
                    f"seeker_competencies[{index}].level has unsupported value: "
                    f"{unsupported_value!r}."
                ),
            )

        if competency.competency_key in seen_keys:
            _raise_input_error(
                code="duplicate_seeker_competency_key",
                message=(
                    f"Duplicate seeker competency_key: "
                    f"{competency.competency_key!r}."
                ),
            )
        seen_keys.add(competency.competency_key)


def _validate_matching_inputs(
    *,
    requirements: list[MatchingRequirementInput],
    seeker_competencies: list[SeekerCompetencyInput],
) -> None:
    _validate_requirements(requirements)
    _validate_seeker_competencies(seeker_competencies)


def calculate_exact_match_result(
    *,
    job_offer_id: int,
    seeker_user_id: int,
    requirements: list[MatchingRequirementInput],
    seeker_competencies: list[SeekerCompetencyInput],
) -> MatchingResultPayload:
    """Calculate deterministic exact-match suitability and explanation payload.

    Deterministic formula per requirement:
    - max_points = weight(priority)
    - expected_level = expected_level(priority)
    - if seeker competency missing: earned = 0
    - if present: earned = max_points * min(seeker_level_numeric / expected_level_numeric, 1.0)
    - point_loss = max_points - earned
    """
    _validate_matching_inputs(
        requirements=requirements,
        seeker_competencies=seeker_competencies,
    )

    seeker_lookup: dict[str, CompetencyLevel] = {}
    for seeker_competency in seeker_competencies:
        seeker_lookup[seeker_competency.competency_key] = seeker_competency.level

    evaluated_rows: list[_EvaluatedRequirement] = []
    for requirement in requirements:
        max_points = float(PRIORITY_WEIGHTS[requirement.priority])
        expected_level = EXPECTED_LEVEL_BY_PRIORITY[requirement.priority]
        seeker_level = seeker_lookup.get(requirement.competency_key)

        if seeker_level is None:
            earned_points = 0.0
            status = "missing"
            reason_code = "missing_competency"
        else:
            expected_level_numeric = LEVEL_NUMERIC[expected_level]
            seeker_level_numeric = LEVEL_NUMERIC[seeker_level]
            ratio = min(seeker_level_numeric / expected_level_numeric, 1.0)
            earned_points = max_points * ratio
            if seeker_level_numeric >= expected_level_numeric:
                status = "matched"
                reason_code = "meets_expected_level"
            else:
                status = "insufficient"
                reason_code = "level_below_expected"

        point_loss = max_points - earned_points
        evaluated_rows.append(
            _EvaluatedRequirement(
                competency_key=requirement.competency_key,
                priority=requirement.priority,
                expected_level=expected_level,
                seeker_level=seeker_level,
                status=status,
                earned_points=earned_points,
                max_points=max_points,
                point_loss=point_loss,
                reason_code=reason_code,
            )
        )

    # Use one sorted row set for every explanation list to avoid ordering drift.
    sorted_rows = sorted(evaluated_rows, key=_sort_key)

    # Totals are computed from evaluated rows (not reconstructed from output lists)
    # to keep score math and explanation payload internally consistent.
    total_earned_points = sum(row.earned_points for row in evaluated_rows)
    total_max_points = sum(row.max_points for row in evaluated_rows)
    matched_count = sum(1 for row in evaluated_rows if row.status == "matched")
    insufficient_count = sum(1 for row in evaluated_rows if row.status == "insufficient")
    missing_count = sum(1 for row in evaluated_rows if row.status == "missing")

    must_have_rows = [
        row
        for row in evaluated_rows
        if row.priority == RequirementPriority.MUST_HAVE
    ]
    must_have_total_count = len(must_have_rows)
    must_have_matched_count = sum(1 for row in must_have_rows if row.status == "matched")
    must_have_insufficient_count = sum(
        1 for row in must_have_rows if row.status == "insufficient"
    )
    must_have_missing_count = sum(1 for row in must_have_rows if row.status == "missing")
    must_have_coverage_ratio = (
        must_have_matched_count / must_have_total_count
        if must_have_total_count > 0
        else 0.0
    )
    # Dual-signal rule: missing must-have competency creates a critical gap warning.
    critical_gap_present = must_have_missing_count > 0

    if total_max_points <= 0:
        # Explicit no-requirements fallback from Phase 3 spec.
        status = "not_applicable_no_requirements"
        score = 0.0
    else:
        score = round((100.0 * total_earned_points) / total_max_points, 1)
        if critical_gap_present:
            status = "ok_with_must_have_gaps"
        else:
            status = "ok"

    breakdown = [
        MatchingBreakdownItem(
            competency_key=row.competency_key,
            priority=row.priority,
            expected_level=row.expected_level,
            seeker_level=row.seeker_level,
            status=row.status,
            earned_points=row.earned_points,
            max_points=row.max_points,
            point_loss=row.point_loss,
            reason_code=row.reason_code,
        )
        for row in sorted_rows
    ]

    missing_competencies = [
        MissingCompetencyItem(
            competency_key=row.competency_key,
            priority=row.priority,
            reason_code=row.reason_code,
        )
        for row in sorted_rows
        if row.status == "missing"
    ]

    insufficient_competencies = [
        InsufficientCompetencyItem(
            competency_key=row.competency_key,
            priority=row.priority,
            expected_level=row.expected_level,
            seeker_level=row.seeker_level,
            reason_code=row.reason_code,
        )
        for row in sorted_rows
        if row.status == "insufficient" and row.seeker_level is not None
    ]

    development_targets = [
        DevelopmentTargetItem(
            competency_key=row.competency_key,
            priority=row.priority,
            suggested_target_level=row.expected_level,
            point_gain_if_reached=row.point_loss,
        )
        for row in sorted_rows
        if row.status != "matched"
    ]

    totals = MatchingTotals(
        earned_points=total_earned_points,
        max_points=total_max_points,
        requirements_count=len(requirements),
        matched_count=matched_count,
        insufficient_count=insufficient_count,
        missing_count=missing_count,
    )
    must_have_coverage = MustHaveCoverage(
        total_count=must_have_total_count,
        matched_count=must_have_matched_count,
        insufficient_count=must_have_insufficient_count,
        missing_count=must_have_missing_count,
        coverage_ratio=must_have_coverage_ratio,
    )
    weights_used = MatchingWeightsUsed(
        priority_weights={
            priority.value: weight for priority, weight in PRIORITY_WEIGHTS.items()
        },
        expected_level_by_priority={
            priority.value: level.value
            for priority, level in EXPECTED_LEVEL_BY_PRIORITY.items()
        },
    )

    return MatchingResultPayload(
        algorithm_version=ALGORITHM_VERSION,
        scope=PRIVATE_PREVIEW_SCOPE,
        job_offer_id=job_offer_id,
        seeker_user_id=seeker_user_id,
        score=score,
        status=status,
        critical_gap_present=critical_gap_present,
        must_have_coverage=must_have_coverage,
        totals=totals,
        weights_used=weights_used,
        breakdown=breakdown,
        missing_competencies=missing_competencies,
        insufficient_competencies=insufficient_competencies,
        development_targets=development_targets,
    )
