from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Application,
    ApplicationSnapshot,
    JobOffer,
    JobOfferStatus,
    JobSeekerCompetency,
    JobSeekerProfile,
    User,
    UserRole,
)

FORBIDDEN_APPLY_MESSAGE = "Only job seekers can apply to job offers."
PUBLISHED_JOB_OFFER_NOT_FOUND_MESSAGE = "Published job offer not found."
SEEKER_PROFILE_NOT_FOUND_MESSAGE = "Seeker profile not found."
DUPLICATE_APPLICATION_MESSAGE = "Application already exists for this seeker and job offer."


def _build_competencies_snapshot(
    *,
    competencies: list[JobSeekerCompetency],
) -> list[dict[str, str]]:
    return [
        {
            "competency_key": item.competency_key,
            "level": item.level.value,
        }
        for item in competencies
    ]


def _normalize_consent_timestamp(*, consent_given_at: datetime | None) -> datetime:
    if consent_given_at is None:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    if consent_given_at.tzinfo is None:
        return consent_given_at
    return consent_given_at.astimezone(timezone.utc).replace(tzinfo=None)


def apply_to_published_job_offer(
    db_session: Session,
    *,
    seeker_user: User,
    job_offer_id: int,
    consent_given_at: datetime | None = None,
) -> Application:
    if seeker_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=FORBIDDEN_APPLY_MESSAGE,
        )

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

    profile = (
        db_session.query(JobSeekerProfile)
        .filter(JobSeekerProfile.user_id == seeker_user.id)
        .one_or_none()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=SEEKER_PROFILE_NOT_FOUND_MESSAGE,
        )

    existing = (
        db_session.query(Application)
        .filter(
            Application.job_offer_id == job_offer.id,
            Application.seeker_user_id == seeker_user.id,
        )
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_APPLICATION_MESSAGE,
        )

    competency_rows = (
        db_session.query(JobSeekerCompetency)
        .filter(JobSeekerCompetency.user_id == seeker_user.id)
        .order_by(JobSeekerCompetency.id.asc())
        .all()
    )
    consent_time = _normalize_consent_timestamp(consent_given_at=consent_given_at)

    application = Application(
        job_offer_id=job_offer.id,
        seeker_user_id=seeker_user.id,
        consent_given_at=consent_time,
    )
    snapshot = ApplicationSnapshot(
        application=application,
        full_name=profile.full_name,
        summary=profile.summary,
        location=profile.location,
        occupation_key=profile.occupation_key,
        competencies=_build_competencies_snapshot(competencies=competency_rows),
        audit_metadata={
            "job_offer_id": str(job_offer.id),
            "job_offer_title": job_offer.title,
            "job_offer_occupation_key": job_offer.occupation_key,
        },
    )
    db_session.add(application)
    db_session.add(snapshot)

    try:
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_APPLICATION_MESSAGE,
        )

    db_session.refresh(application)
    return application


def list_applications_for_seeker(
    db_session: Session,
    *,
    seeker_user_id: int,
) -> list[Application]:
    return (
        db_session.query(Application)
        .filter(Application.seeker_user_id == seeker_user_id)
        .order_by(Application.created_at.desc(), Application.id.desc())
        .all()
    )
