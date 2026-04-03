from app.db.models import CompetencyLevel, RequirementPriority
from app.modules.matching.engine import calculate_exact_match_result
from app.modules.matching.schemas import MatchingRequirementInput, SeekerCompetencyInput


def _requirement(competency_key: str, priority: RequirementPriority) -> MatchingRequirementInput:
    return MatchingRequirementInput(competency_key=competency_key, priority=priority)


def _competency(competency_key: str, level: CompetencyLevel) -> SeekerCompetencyInput:
    return SeekerCompetencyInput(competency_key=competency_key, level=level)


def test_full_match_returns_100_score_and_no_gaps():
    result = calculate_exact_match_result(
        job_offer_id=101,
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

    assert result.algorithm_version == "v1_exact_priority_level"
    assert result.scope == "private_preview"
    assert result.status == "ok"
    assert result.score == 100.0
    assert result.totals.earned_points == 9.0
    assert result.totals.max_points == 9.0
    assert result.totals.requirements_count == 3
    assert result.totals.matched_count == 3
    assert result.totals.insufficient_count == 0
    assert result.totals.missing_count == 0
    assert result.missing_competencies == []
    assert result.insufficient_competencies == []
    assert result.development_targets == []
    assert [item.status for item in result.breakdown] == ["matched", "matched", "matched"]
    assert result.weights_used.priority_weights == {
        "must_have": 5,
        "important": 3,
        "nice_to_have": 1,
    }
    assert result.weights_used.expected_level_by_priority == {
        "must_have": "intermediate",
        "important": "intermediate",
        "nice_to_have": "beginner",
    }


def test_missing_competency_is_classified_and_scored_as_zero():
    result = calculate_exact_match_result(
        job_offer_id=102,
        seeker_user_id=18,
        requirements=[_requirement("comp_api", RequirementPriority.MUST_HAVE)],
        seeker_competencies=[],
    )

    assert result.status == "ok"
    assert result.score == 0.0
    assert result.totals.earned_points == 0.0
    assert result.totals.max_points == 5.0
    assert result.totals.matched_count == 0
    assert result.totals.insufficient_count == 0
    assert result.totals.missing_count == 1
    assert len(result.breakdown) == 1
    assert result.breakdown[0].status == "missing"
    assert result.breakdown[0].reason_code == "missing_competency"
    assert result.breakdown[0].earned_points == 0.0
    assert result.breakdown[0].point_loss == 5.0
    assert len(result.missing_competencies) == 1
    assert result.missing_competencies[0].competency_key == "comp_api"
    assert result.missing_competencies[0].reason_code == "missing_competency"
    assert result.insufficient_competencies == []
    assert len(result.development_targets) == 1
    assert result.development_targets[0].point_gain_if_reached == 5.0


def test_insufficient_level_gets_partial_points():
    result = calculate_exact_match_result(
        job_offer_id=103,
        seeker_user_id=19,
        requirements=[_requirement("comp_sql", RequirementPriority.IMPORTANT)],
        seeker_competencies=[_competency("comp_sql", CompetencyLevel.BEGINNER)],
    )

    assert result.status == "ok"
    assert result.score == 50.0
    assert result.totals.earned_points == 1.5
    assert result.totals.max_points == 3.0
    assert result.totals.matched_count == 0
    assert result.totals.insufficient_count == 1
    assert result.totals.missing_count == 0
    assert len(result.breakdown) == 1
    assert result.breakdown[0].status == "insufficient"
    assert result.breakdown[0].reason_code == "level_below_expected"
    assert result.breakdown[0].earned_points == 1.5
    assert result.breakdown[0].point_loss == 1.5
    assert result.missing_competencies == []
    assert len(result.insufficient_competencies) == 1
    assert result.insufficient_competencies[0].competency_key == "comp_sql"
    assert result.insufficient_competencies[0].seeker_level == CompetencyLevel.BEGINNER
    assert len(result.development_targets) == 1
    assert result.development_targets[0].point_gain_if_reached == 1.5


def test_weighted_mixed_priorities_score_is_correct():
    result = calculate_exact_match_result(
        job_offer_id=104,
        seeker_user_id=20,
        requirements=[
            _requirement("comp_api", RequirementPriority.MUST_HAVE),
            _requirement("comp_sql", RequirementPriority.IMPORTANT),
            _requirement("comp_docs", RequirementPriority.NICE_TO_HAVE),
        ],
        seeker_competencies=[
            _competency("comp_api", CompetencyLevel.INTERMEDIATE),
            _competency("comp_sql", CompetencyLevel.BEGINNER),
        ],
    )

    assert result.status == "ok"
    assert result.totals.earned_points == 6.5
    assert result.totals.max_points == 9.0
    assert result.score == 72.2
    assert result.totals.matched_count == 1
    assert result.totals.insufficient_count == 1
    assert result.totals.missing_count == 1
    assert [item.status for item in result.breakdown] == ["matched", "insufficient", "missing"]


def test_no_requirements_returns_not_applicable_status():
    result = calculate_exact_match_result(
        job_offer_id=105,
        seeker_user_id=21,
        requirements=[],
        seeker_competencies=[_competency("comp_unused", CompetencyLevel.ADVANCED)],
    )

    assert result.status == "not_applicable_no_requirements"
    assert result.score == 0.0
    assert result.totals.earned_points == 0.0
    assert result.totals.max_points == 0.0
    assert result.totals.requirements_count == 0
    assert result.totals.matched_count == 0
    assert result.totals.insufficient_count == 0
    assert result.totals.missing_count == 0
    assert result.breakdown == []
    assert result.missing_competencies == []
    assert result.insufficient_competencies == []
    assert result.development_targets == []


def test_output_ordering_is_deterministic_across_lists():
    result = calculate_exact_match_result(
        job_offer_id=106,
        seeker_user_id=22,
        requirements=[
            _requirement("comp_d", RequirementPriority.IMPORTANT),
            _requirement("comp_b", RequirementPriority.MUST_HAVE),
            _requirement("comp_e", RequirementPriority.NICE_TO_HAVE),
            _requirement("comp_f", RequirementPriority.MUST_HAVE),
            _requirement("comp_c", RequirementPriority.IMPORTANT),
            _requirement("comp_a", RequirementPriority.MUST_HAVE),
        ],
        seeker_competencies=[_competency("comp_f", CompetencyLevel.BEGINNER)],
    )

    assert [item.competency_key for item in result.breakdown] == [
        "comp_a",
        "comp_b",
        "comp_f",
        "comp_c",
        "comp_d",
        "comp_e",
    ]
    assert [item.status for item in result.breakdown] == [
        "missing",
        "missing",
        "insufficient",
        "missing",
        "missing",
        "missing",
    ]
    assert [item.competency_key for item in result.missing_competencies] == [
        "comp_a",
        "comp_b",
        "comp_c",
        "comp_d",
        "comp_e",
    ]
    assert [item.competency_key for item in result.insufficient_competencies] == [
        "comp_f"
    ]
    assert [item.competency_key for item in result.development_targets] == [
        "comp_a",
        "comp_b",
        "comp_f",
        "comp_c",
        "comp_d",
        "comp_e",
    ]
