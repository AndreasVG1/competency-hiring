from app.modules.matching.schemas import (
    MatchingRequirementInput,
    MatchingResultPayload,
    SeekerCompetencyInput,
)

ALGORITHM_VERSION = "v1_exact_priority_level"
PRIVATE_PREVIEW_SCOPE = "private_preview"


def calculate_exact_match_result(
    *,
    job_offer_id: int,
    seeker_user_id: int,
    requirements: list[MatchingRequirementInput],
    seeker_competencies: list[SeekerCompetencyInput],
) -> MatchingResultPayload:
    """Calculate deterministic exact-match suitability and explanation payload.

    Business logic intentionally deferred to Phase 3 step 3.
    """
    del job_offer_id, seeker_user_id, requirements, seeker_competencies
    raise NotImplementedError("Phase 3 step 3: matching engine logic is not implemented yet.")
