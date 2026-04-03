from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import JobOffer, JobOfferRequirement, JobOfferStatus, JobSeekerCompetency
from app.modules.matching.engine import (
    MatchingInputValidationError,
    calculate_exact_match_result,
)
from app.modules.matching.schemas import (
    MatchingRequirementInput,
    MatchingResultPayload,
    SeekerCompetencyInput,
)

PUBLISHED_JOB_OFFER_NOT_FOUND_MESSAGE = "Published job offer not found."


def _get_published_job_offer_or_404(
    db_session: Session,
    *,
    job_offer_id: int,
) -> JobOffer:
    job_offer = (
        db_session.query(JobOffer)
        .filter(
            JobOffer.id == job_offer_id,
            JobOffer.status == JobOfferStatus.PUBLISHED,
        )
        .one_or_none()
    )
    if job_offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PUBLISHED_JOB_OFFER_NOT_FOUND_MESSAGE,
        )
    return job_offer


def _list_job_offer_requirements(
    db_session: Session,
    *,
    job_offer_id: int,
) -> list[MatchingRequirementInput]:
    rows = (
        db_session.query(JobOfferRequirement)
        .filter(JobOfferRequirement.job_offer_id == job_offer_id)
        .order_by(JobOfferRequirement.id.asc())
        .all()
    )
    return [
        MatchingRequirementInput(
            competency_key=row.competency_key,
            priority=row.priority,
        )
        for row in rows
    ]


def _list_seeker_competencies(
    db_session: Session,
    *,
    seeker_user_id: int,
) -> list[SeekerCompetencyInput]:
    rows = (
        db_session.query(JobSeekerCompetency)
        .filter(JobSeekerCompetency.user_id == seeker_user_id)
        .order_by(JobSeekerCompetency.id.asc())
        .all()
    )
    return [
        SeekerCompetencyInput(
            competency_key=row.competency_key,
            level=row.level,
        )
        for row in rows
    ]


def get_private_analysis_for_seeker(
    db_session: Session,
    *,
    seeker_user_id: int,
    job_offer_id: int,
) -> MatchingResultPayload:
    _get_published_job_offer_or_404(db_session, job_offer_id=job_offer_id)

    requirements = _list_job_offer_requirements(
        db_session,
        job_offer_id=job_offer_id,
    )
    competencies = _list_seeker_competencies(
        db_session,
        seeker_user_id=seeker_user_id,
    )

    try:
        return calculate_exact_match_result(
            job_offer_id=job_offer_id,
            seeker_user_id=seeker_user_id,
            requirements=requirements,
            seeker_competencies=competencies,
        )
    except MatchingInputValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid matching input: {exc.code}: {exc.message}",
        ) from exc
