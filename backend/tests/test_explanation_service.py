import pytest

from app.db.models import CompetencyLevel, RequirementPriority
from app.modules.explanation.service import build_explanation
from app.modules.explanation.schemas import ExplanationInputValidationError
from app.modules.matching.engine import calculate_exact_match_result
from app.modules.matching.schemas import MatchingRequirementInput, SeekerCompetencyInput


def _requirement(competency_key: str, priority: RequirementPriority) -> MatchingRequirementInput:
    return MatchingRequirementInput(competency_key=competency_key, priority=priority)


def _competency(competency_key: str, level: CompetencyLevel) -> SeekerCompetencyInput:
    return SeekerCompetencyInput(competency_key=competency_key, level=level)


def test_full_match_builds_strength_summary_without_gaps_for_seeker():
    payload = calculate_exact_match_result(
        job_offer_id=1001,
        seeker_user_id=17,
        requirements=[
            _requirement("comp_python", RequirementPriority.MUST_HAVE),
            _requirement("comp_sql", RequirementPriority.IMPORTANT),
            _requirement("comp_docs", RequirementPriority.NICE_TO_HAVE),
        ],
        seeker_competencies=[
            _competency("comp_python", CompetencyLevel.ADVANCED),
            _competency("comp_sql", CompetencyLevel.INTERMEDIATE),
            _competency("comp_docs", CompetencyLevel.BEGINNER),
        ],
    )

    explanation = build_explanation(payload, "seeker")

    assert explanation.audience == "seeker"
    assert explanation.algorithm_version == "v2_exact_priority_level_dual_signal"
    assert explanation.summary.headline == "Current suitability score: 100.0/100."
    assert explanation.summary.status_label == "Current profile alignment is acceptable."
    assert explanation.summary.must_have_notice is None
    assert explanation.summary.no_requirements_notice is None
    assert len(explanation.highlights) == 3
    assert explanation.gaps == []
    assert explanation.development_roadmap == []


def test_mixed_missing_and_insufficient_creates_gap_text_and_must_have_notice():
    payload = calculate_exact_match_result(
        job_offer_id=1002,
        seeker_user_id=18,
        requirements=[
            _requirement("comp_api", RequirementPriority.MUST_HAVE),
            _requirement("comp_sql", RequirementPriority.IMPORTANT),
        ],
        seeker_competencies=[_competency("comp_sql", CompetencyLevel.BEGINNER)],
    )

    explanation = build_explanation(payload, "seeker")

    assert explanation.summary.must_have_notice == (
        "At least one must-have competency is currently missing."
    )
    assert [item.competency_key for item in explanation.gaps] == ["comp_api", "comp_sql"]
    assert explanation.gaps[0].reason_code == "missing_competency"
    assert explanation.gaps[0].text == "Missing must-have competency: comp_api."
    assert explanation.gaps[1].reason_code == "level_below_expected"
    assert explanation.gaps[1].text == (
        "comp_sql is below expected level (beginner vs expected intermediate)."
    )


def test_no_requirements_sets_explicit_summary_and_empty_lists():
    payload = calculate_exact_match_result(
        job_offer_id=1003,
        seeker_user_id=19,
        requirements=[],
        seeker_competencies=[_competency("comp_extra", CompetencyLevel.ADVANCED)],
    )

    explanation = build_explanation(payload, "seeker")

    assert explanation.summary.no_requirements_notice == (
        "This job offer has no defined competency requirements, so no suitability "
        "scoring comparison was possible."
    )
    assert explanation.highlights == []
    assert explanation.gaps == []
    assert explanation.development_roadmap == []


def test_recruiter_audience_suppresses_roadmap_while_seeker_keeps_it():
    payload = calculate_exact_match_result(
        job_offer_id=1004,
        seeker_user_id=20,
        requirements=[_requirement("comp_sql", RequirementPriority.IMPORTANT)],
        seeker_competencies=[_competency("comp_sql", CompetencyLevel.BEGINNER)],
    )

    seeker_explanation = build_explanation(payload, "seeker")
    recruiter_explanation = build_explanation(payload, "recruiter")

    assert seeker_explanation.development_roadmap is not None
    assert len(seeker_explanation.development_roadmap) == 1
    assert recruiter_explanation.development_roadmap is None


def test_deterministic_ordering_is_applied_for_highlights_gaps_and_roadmap():
    payload = calculate_exact_match_result(
        job_offer_id=1005,
        seeker_user_id=21,
        requirements=[
            _requirement("comp_c", RequirementPriority.IMPORTANT),
            _requirement("comp_b", RequirementPriority.MUST_HAVE),
            _requirement("comp_a", RequirementPriority.MUST_HAVE),
            _requirement("comp_g", RequirementPriority.IMPORTANT),
            _requirement("comp_f", RequirementPriority.MUST_HAVE),
            _requirement("comp_e", RequirementPriority.NICE_TO_HAVE),
            _requirement("comp_d", RequirementPriority.IMPORTANT),
        ],
        seeker_competencies=[
            _competency("comp_d", CompetencyLevel.BEGINNER),
            _competency("comp_e", CompetencyLevel.BEGINNER),
            _competency("comp_f", CompetencyLevel.INTERMEDIATE),
            _competency("comp_g", CompetencyLevel.ADVANCED),
        ],
    )

    payload_as_dict = payload.model_dump(mode="json")
    payload_as_dict["breakdown"] = list(reversed(payload_as_dict["breakdown"]))
    payload_as_dict["development_targets"] = list(
        reversed(payload_as_dict["development_targets"])
    )

    explanation = build_explanation(payload_as_dict, "seeker")

    assert [item.competency_key for item in explanation.highlights] == [
        "comp_f",
        "comp_g",
        "comp_e",
    ]
    assert [item.competency_key for item in explanation.gaps] == [
        "comp_a",
        "comp_b",
        "comp_c",
        "comp_d",
    ]
    assert [item.competency_key for item in explanation.development_roadmap or []] == [
        "comp_a",
        "comp_b",
        "comp_c",
        "comp_d",
    ]


def test_unknown_algorithm_returns_fallback_without_raising():
    payload = calculate_exact_match_result(
        job_offer_id=1006,
        seeker_user_id=22,
        requirements=[_requirement("comp_sql", RequirementPriority.IMPORTANT)],
        seeker_competencies=[_competency("comp_sql", CompetencyLevel.BEGINNER)],
    ).model_dump(mode="json")
    payload["algorithm_version"] = "v999_future_algorithm"

    explanation = build_explanation(payload, "seeker")

    assert explanation.algorithm_version == "v999_future_algorithm"
    assert explanation.highlights == []
    assert explanation.gaps == []
    assert explanation.development_roadmap == []
    assert explanation.transparency_notes[-1] == (
        "Detailed explanation templates are unavailable for algorithm version "
        "v999_future_algorithm; showing minimal summary with raw payload preserved."
    )


def test_invalid_payload_shape_raises_typed_validation_error_with_stable_message():
    with pytest.raises(ExplanationInputValidationError) as exc_info:
        build_explanation({"unexpected": "payload"}, "seeker")

    assert exc_info.value.code == "invalid_payload"
    assert (
        exc_info.value.message
        == "Payload does not match MatchingResultPayload schema."
    )
