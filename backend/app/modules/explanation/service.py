from collections.abc import Callable
from typing import NoReturn, cast

from pydantic import ValidationError

from app.db.models import RequirementPriority
from app.modules.explanation.schemas import (
    ExplanationAudience,
    ExplanationGapItem,
    ExplanationHighlightItem,
    ExplanationI18nMessage,
    ExplanationInputValidationError,
    ExplanationRoadmapItem,
    ExplanationSummary,
    MatchingExplanation,
)
from app.modules.explanation.templates import (
    BASE_TRANSPARENCY_NOTES,
    DECISION_SUPPORT_NOTICE,
    FALLBACK_STATUS_LABEL,
    INSUFFICIENT_REASON_TEMPLATE,
    MATCHED_REASON_TEMPLATE,
    MISSING_REASON_TEMPLATE,
    MUST_HAVE_NOTICE,
    NO_REQUIREMENTS_NOTICE,
    PRIORITY_LABEL_BY_VALUE,
    ROADMAP_TEMPLATE,
    STATUS_LABEL_BY_RESULT,
    SUMMARY_HEADLINE_TEMPLATE,
    UNKNOWN_ALGORITHM_NOTE_TEMPLATE,
)
from app.modules.matching.schemas import MatchingBreakdownItem, MatchingResultPayload

SUPPORTED_ALGORITHM_VERSION = "v2_exact_priority_level_dual_signal"

PRIORITY_SORT_RANK = {
    RequirementPriority.MUST_HAVE: 0,
    RequirementPriority.IMPORTANT: 1,
    RequirementPriority.NICE_TO_HAVE: 2,
}

SUMMARY_HEADLINE_CODE = "summary.headline.score_out_of_100"
SUMMARY_STATUS_CODE_PREFIX = "summary.status."
SUMMARY_NOTICE_DECISION_SUPPORT_CODE = "summary.notice.decision_support"
SUMMARY_NOTICE_MUST_HAVE_GAP_CODE = "summary.notice.must_have_gap"
SUMMARY_NOTICE_NO_REQUIREMENTS_CODE = "summary.notice.no_requirements"

HIGHLIGHT_MATCHED_CODE = "highlight.matched_expected_level"
GAP_MISSING_CODE = "gap.missing_competency"
GAP_INSUFFICIENT_CODE = "gap.level_below_expected"
GAP_GENERIC_CODE = "gap.generic"
ROADMAP_IMPROVEMENT_CODE = "roadmap.improve_to_level_recover_points"

TRANSPARENCY_EXACT_MATCHING_CODE = "transparency.exact_key_matching_only"
TRANSPARENCY_DETERMINISTIC_CODE = "transparency.deterministic_priority_weights_and_levels"
TRANSPARENCY_NO_INFERENCE_CODE = "transparency.no_semantic_inference"
TRANSPARENCY_UNKNOWN_ALGORITHM_CODE = "transparency.unknown_algorithm_version"

_FULL_RENDERERS: dict[str, Callable[[MatchingResultPayload, ExplanationAudience], MatchingExplanation]] = {}


def _raise_validation_error(*, code: str, message: str) -> NoReturn:
    raise ExplanationInputValidationError(code=code, message=message)


def _normalize_audience(audience: ExplanationAudience) -> ExplanationAudience:
    if audience in ("seeker", "recruiter"):
        return cast(ExplanationAudience, audience)
    _raise_validation_error(
        code="invalid_audience",
        message="Audience must be one of: seeker, recruiter.",
    )


def _normalize_payload(
    payload: MatchingResultPayload | dict[str, object],
) -> MatchingResultPayload:
    if isinstance(payload, MatchingResultPayload):
        return payload

    if not isinstance(payload, dict):
        _raise_validation_error(
            code="invalid_payload_type",
            message="Payload must be a MatchingResultPayload instance or dictionary.",
        )

    try:
        return MatchingResultPayload.model_validate(payload)
    except ValidationError:
        _raise_validation_error(
            code="invalid_payload",
            message="Payload does not match MatchingResultPayload schema.",
        )


def _priority_label(priority: RequirementPriority) -> str:
    return PRIORITY_LABEL_BY_VALUE.get(priority.value, priority.value)


def _status_label(status: str) -> str:
    return STATUS_LABEL_BY_RESULT.get(status, FALLBACK_STATUS_LABEL)


def _breakdown_sort_key(item: MatchingBreakdownItem) -> tuple[int, float, str]:
    return (
        PRIORITY_SORT_RANK.get(item.priority, 999),
        -item.point_loss,
        item.competency_key,
    )


def _roadmap_sort_key(item: ExplanationRoadmapItem) -> tuple[int, float, str]:
    return (
        PRIORITY_SORT_RANK.get(item.priority, 999),
        -item.estimated_point_gain,
        item.competency_key,
    )


def _build_summary(payload: MatchingResultPayload) -> ExplanationSummary:
    return ExplanationSummary(
        headline=SUMMARY_HEADLINE_TEMPLATE.format(score=payload.score),
        headline_code=SUMMARY_HEADLINE_CODE,
        headline_params={"score": payload.score},
        status_label=_status_label(payload.status),
        status_code=f"{SUMMARY_STATUS_CODE_PREFIX}{payload.status}",
        decision_support_notice=DECISION_SUPPORT_NOTICE,
        decision_support_notice_code=SUMMARY_NOTICE_DECISION_SUPPORT_CODE,
        must_have_notice=MUST_HAVE_NOTICE if payload.critical_gap_present else None,
        must_have_notice_code=(
            SUMMARY_NOTICE_MUST_HAVE_GAP_CODE if payload.critical_gap_present else None
        ),
        no_requirements_notice=(
            NO_REQUIREMENTS_NOTICE
            if payload.status == "not_applicable_no_requirements"
            else None
        ),
        no_requirements_notice_code=(
            SUMMARY_NOTICE_NO_REQUIREMENTS_CODE
            if payload.status == "not_applicable_no_requirements"
            else None
        ),
    )


def _build_highlights(rows: list[MatchingBreakdownItem]) -> list[ExplanationHighlightItem]:
    return [
        ExplanationHighlightItem(
            competency_key=row.competency_key,
            priority=row.priority,
            text=MATCHED_REASON_TEMPLATE.format(
                competency_key=row.competency_key,
                priority_label=_priority_label(row.priority),
            ),
            text_code=HIGHLIGHT_MATCHED_CODE,
            text_params={
                "competency_key": row.competency_key,
                "priority": row.priority.value,
            },
        )
        for row in rows
        if row.status == "matched"
    ]


def _gap_text(row: MatchingBreakdownItem) -> str:
    if row.reason_code == "missing_competency":
        return MISSING_REASON_TEMPLATE.format(
            priority_label=_priority_label(row.priority),
            competency_key=row.competency_key,
        )

    if row.reason_code == "level_below_expected" and row.seeker_level is not None:
        return INSUFFICIENT_REASON_TEMPLATE.format(
            competency_key=row.competency_key,
            current_level=row.seeker_level.value,
            expected_level=row.expected_level.value,
        )

    return f"Gap identified for {row.competency_key}."


def _gap_i18n(row: MatchingBreakdownItem) -> tuple[str, dict[str, object]]:
    if row.reason_code == "missing_competency":
        return (
            GAP_MISSING_CODE,
            {
                "competency_key": row.competency_key,
                "priority": row.priority.value,
            },
        )

    if (
        row.reason_code == "level_below_expected"
        and row.seeker_level is not None
        and row.expected_level is not None
    ):
        return (
            GAP_INSUFFICIENT_CODE,
            {
                "competency_key": row.competency_key,
                "current_level": row.seeker_level.value,
                "expected_level": row.expected_level.value,
            },
        )

    return (
        GAP_GENERIC_CODE,
        {
            "competency_key": row.competency_key,
        },
    )


def _build_gaps(rows: list[MatchingBreakdownItem]) -> list[ExplanationGapItem]:
    gaps: list[ExplanationGapItem] = []
    for row in rows:
        if row.status == "matched":
            continue

        text_code, text_params = _gap_i18n(row)
        kind = "missing" if row.status == "missing" else "insufficient"
        gaps.append(
            ExplanationGapItem(
                kind=kind,
                competency_key=row.competency_key,
                priority=row.priority,
                reason_code=row.reason_code,
                expected_level=row.expected_level,
                current_level=row.seeker_level,
                text=_gap_text(row),
                text_code=text_code,
                text_params=text_params,
            )
        )

    return gaps


def _build_roadmap(
    payload: MatchingResultPayload,
    *,
    audience: ExplanationAudience,
) -> list[ExplanationRoadmapItem] | None:
    if audience == "recruiter":
        return None

    roadmap_items = sorted(
        [
            ExplanationRoadmapItem(
                competency_key=item.competency_key,
                priority=item.priority,
                target_level=item.suggested_target_level,
                estimated_point_gain=item.point_gain_if_reached,
                text=ROADMAP_TEMPLATE.format(
                    competency_key=item.competency_key,
                    target_level=item.suggested_target_level.value,
                    point_gain=item.point_gain_if_reached,
                ),
                text_code=ROADMAP_IMPROVEMENT_CODE,
                text_params={
                    "competency_key": item.competency_key,
                    "target_level": item.suggested_target_level.value,
                    "point_gain": item.point_gain_if_reached,
                },
            )
            for item in payload.development_targets
        ],
        key=_roadmap_sort_key,
    )
    return roadmap_items


def _build_transparency_notes_i18n(
    payload: MatchingResultPayload,
    *,
    include_unknown_algorithm_note: bool,
) -> list[ExplanationI18nMessage]:
    notes: list[ExplanationI18nMessage] = [
        ExplanationI18nMessage(code=TRANSPARENCY_EXACT_MATCHING_CODE),
        ExplanationI18nMessage(code=TRANSPARENCY_DETERMINISTIC_CODE),
        ExplanationI18nMessage(code=TRANSPARENCY_NO_INFERENCE_CODE),
    ]

    if include_unknown_algorithm_note:
        notes.append(
            ExplanationI18nMessage(
                code=TRANSPARENCY_UNKNOWN_ALGORITHM_CODE,
                params={"algorithm_version": payload.algorithm_version},
            )
        )

    return notes


def _render_known_v2(
    payload: MatchingResultPayload,
    audience: ExplanationAudience,
) -> MatchingExplanation:
    sorted_rows = sorted(payload.breakdown, key=_breakdown_sort_key)
    return MatchingExplanation(
        audience=audience,
        algorithm_version=payload.algorithm_version,
        summary=_build_summary(payload),
        highlights=_build_highlights(sorted_rows),
        gaps=_build_gaps(sorted_rows),
        development_roadmap=_build_roadmap(payload, audience=audience),
        transparency_notes=list(BASE_TRANSPARENCY_NOTES),
        transparency_notes_i18n=_build_transparency_notes_i18n(
            payload, include_unknown_algorithm_note=False
        ),
    )


def _render_fallback(
    payload: MatchingResultPayload,
    audience: ExplanationAudience,
) -> MatchingExplanation:
    transparency_notes = [
        *BASE_TRANSPARENCY_NOTES,
        UNKNOWN_ALGORITHM_NOTE_TEMPLATE.format(
            algorithm_version=payload.algorithm_version
        ),
    ]
    return MatchingExplanation(
        audience=audience,
        algorithm_version=payload.algorithm_version,
        summary=_build_summary(payload),
        highlights=[],
        gaps=[],
        development_roadmap=None if audience == "recruiter" else [],
        transparency_notes=transparency_notes,
        transparency_notes_i18n=_build_transparency_notes_i18n(
            payload, include_unknown_algorithm_note=True
        ),
    )


_FULL_RENDERERS[SUPPORTED_ALGORITHM_VERSION] = _render_known_v2


def build_explanation(
    payload: MatchingResultPayload | dict[str, object],
    audience: ExplanationAudience,
) -> MatchingExplanation:
    normalized_payload = _normalize_payload(payload)
    normalized_audience = _normalize_audience(audience)

    renderer = _FULL_RENDERERS.get(normalized_payload.algorithm_version)
    if renderer is None:
        return _render_fallback(normalized_payload, normalized_audience)

    return renderer(normalized_payload, normalized_audience)
