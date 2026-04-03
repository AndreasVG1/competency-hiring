from fastapi import HTTPException
import pytest

from app.db.models import (
    CompetencyLevel,
    JobOffer,
    JobOfferRequirement,
    JobOfferStatus,
    JobSeekerCompetency,
    RequirementPriority,
    User,
    UserRole,
)
from app.modules.matching.engine import MatchingInputValidationError
from app.modules.matching import service


def _create_user(db_session, *, email: str, role: UserRole) -> User:
    user = User(email=email, password_hash="hashed", role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_published_offer(db_session, *, recruiter_user_id: int) -> JobOffer:
    offer = JobOffer(
        recruiter_user_id=recruiter_user_id,
        title="Backend Engineer",
        occupation_key="backend_engineer",
        description="Build APIs",
        status=JobOfferStatus.PUBLISHED,
    )
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)
    return offer


def test_private_analysis_translates_engine_input_validation_to_http_422(
    db_session,
    monkeypatch,
):
    recruiter = _create_user(
        db_session,
        email="matching-service-recruiter-validation@example.com",
        role=UserRole.RECRUITER,
    )
    offer = _create_published_offer(db_session, recruiter_user_id=recruiter.id)

    def _raise_validation_error(**_kwargs):
        raise MatchingInputValidationError(
            code="duplicate_requirement_competency_key",
            message="Duplicate requirement competency_key: 'comp_api'.",
        )

    monkeypatch.setattr(service, "calculate_exact_match_result", _raise_validation_error)

    with pytest.raises(HTTPException) as exc_info:
        service.get_private_analysis_for_seeker(
            db_session,
            seeker_user_id=999999,
            job_offer_id=offer.id,
        )

    assert exc_info.value.status_code == 422
    assert (
        exc_info.value.detail
        == "Invalid matching input: duplicate_requirement_competency_key: "
        "Duplicate requirement competency_key: 'comp_api'."
    )


def test_private_analysis_returns_404_for_missing_offer(db_session):
    with pytest.raises(HTTPException) as exc_info:
        service.get_private_analysis_for_seeker(
            db_session,
            seeker_user_id=123,
            job_offer_id=999999,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Published job offer not found."


def test_private_analysis_returns_404_for_unpublished_offer(db_session):
    recruiter = _create_user(
        db_session,
        email="matching-service-recruiter-unpublished@example.com",
        role=UserRole.RECRUITER,
    )
    draft_offer = JobOffer(
        recruiter_user_id=recruiter.id,
        title="Draft Backend Engineer",
        occupation_key="backend_engineer",
        description="Draft only",
        status=JobOfferStatus.DRAFT,
    )
    db_session.add(draft_offer)
    db_session.commit()
    db_session.refresh(draft_offer)

    with pytest.raises(HTTPException) as exc_info:
        service.get_private_analysis_for_seeker(
            db_session,
            seeker_user_id=123,
            job_offer_id=draft_offer.id,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Published job offer not found."


def test_private_analysis_happy_path_returns_matching_result_payload(db_session):
    recruiter = _create_user(
        db_session,
        email="matching-service-recruiter-happy@example.com",
        role=UserRole.RECRUITER,
    )
    seeker = _create_user(
        db_session,
        email="matching-service-seeker-happy@example.com",
        role=UserRole.JOB_SEEKER,
    )
    offer = _create_published_offer(db_session, recruiter_user_id=recruiter.id)

    db_session.add_all(
        [
            JobOfferRequirement(
                job_offer_id=offer.id,
                competency_key="comp_api",
                priority=RequirementPriority.MUST_HAVE,
            ),
            JobOfferRequirement(
                job_offer_id=offer.id,
                competency_key="comp_sql",
                priority=RequirementPriority.IMPORTANT,
            ),
            JobSeekerCompetency(
                user_id=seeker.id,
                competency_key="comp_api",
                level=CompetencyLevel.INTERMEDIATE,
            ),
        ]
    )
    db_session.commit()

    result = service.get_private_analysis_for_seeker(
        db_session,
        seeker_user_id=seeker.id,
        job_offer_id=offer.id,
    )

    assert result.job_offer_id == offer.id
    assert result.seeker_user_id == seeker.id
    assert result.algorithm_version == "v2_exact_priority_level_dual_signal"
    assert result.scope == "private_preview"
    assert result.status == "ok"
    assert result.score == 62.5
    assert result.totals.requirements_count == 2
    assert result.totals.matched_count == 1
    assert result.totals.insufficient_count == 0
    assert result.totals.missing_count == 1
