from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Application,
    ApplicationMatchingSnapshot,
    ApplicationSnapshot,
    JobOffer,
    JobOfferStatus,
    JobSeekerCompetency,
    JobSeekerProfile,
    User,
    UserRole,
)
from app.modules.explanation import (
    ExplanationInputValidationError,
    build_explanation,
)
from app.modules.matching.engine import MatchingInputValidationError
from app.modules.matching.service import calculate_matching_for_job_offer_and_seeker

FORBIDDEN_APPLY_MESSAGE = "Only job seekers can apply to job offers."
PUBLISHED_JOB_OFFER_NOT_FOUND_MESSAGE = "Published job offer not found."
SEEKER_PROFILE_NOT_FOUND_MESSAGE = "Seeker profile not found."
DUPLICATE_APPLICATION_MESSAGE = "Application already exists for this seeker and job offer."
JOB_OFFER_NOT_FOUND_MESSAGE = "Job offer not found."
APPLICATION_NOT_FOUND_MESSAGE = "Application not found."
SHARED_APPLICATION_SNAPSHOT_SCOPE = "shared_application_snapshot"


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


def _build_shared_matching_for_recruiter(
    *,
    matching_snapshot: ApplicationMatchingSnapshot,
) -> dict[str, object]:
    explanation = None
    try:
        explanation = build_explanation(
            matching_snapshot.result_payload,
            "recruiter",
        ).model_dump(mode="json")
    except ExplanationInputValidationError:
        # Keep applicant list readable even if an old/invalid snapshot payload cannot
        # be normalized for explanation rendering.
        explanation = None

    return {
        "algorithm_version": matching_snapshot.algorithm_version,
        "score": matching_snapshot.score,
        "snapshot_created_at": matching_snapshot.created_at,
        "result_payload": matching_snapshot.result_payload,
        "explanation": explanation,
    }


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

    try:
        matching_result = calculate_matching_for_job_offer_and_seeker(
            db_session,
            seeker_user_id=seeker_user.id,
            job_offer_id=job_offer.id,
        )
        matching_payload = matching_result.model_dump(mode="json")
        matching_payload["scope"] = SHARED_APPLICATION_SNAPSHOT_SCOPE

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
        matching_snapshot = ApplicationMatchingSnapshot(
            application=application,
            algorithm_version=matching_result.algorithm_version,
            score=matching_result.score,
            result_payload=matching_payload,
        )
        db_session.add(application)
        db_session.add(snapshot)
        db_session.add(matching_snapshot)
        db_session.commit()
    except MatchingInputValidationError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid matching input: {exc.code}: {exc.message}",
        ) from exc
    except IntegrityError:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_APPLICATION_MESSAGE,
        )
    except Exception:
        db_session.rollback()
        raise

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


def delete_application_for_seeker(
    db_session: Session,
    *,
    seeker_user_id: int,
    application_id: int,
) -> None:
    application = (
        db_session.query(Application)
        .filter(
            Application.id == application_id,
            Application.seeker_user_id == seeker_user_id,
        )
        .one_or_none()
    )
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=APPLICATION_NOT_FOUND_MESSAGE,
        )

    db_session.delete(application)
    db_session.commit()


def list_applicants_for_owned_job_offer(
    db_session: Session,
    *,
    recruiter_user_id: int,
    job_offer_id: int,
) -> list[dict[str, object]]:
    owned_offer = (
        db_session.query(JobOffer)
        .filter(
            JobOffer.id == job_offer_id,
            JobOffer.recruiter_user_id == recruiter_user_id,
        )
        .one_or_none()
    )
    if owned_offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=JOB_OFFER_NOT_FOUND_MESSAGE,
        )

    rows = (
        db_session.query(Application, ApplicationSnapshot, ApplicationMatchingSnapshot)
        .join(ApplicationSnapshot, ApplicationSnapshot.application_id == Application.id)
        .outerjoin(
            ApplicationMatchingSnapshot,
            ApplicationMatchingSnapshot.application_id == Application.id,
        )
        .filter(Application.job_offer_id == job_offer_id)
        .order_by(Application.created_at.desc(), Application.id.desc())
        .all()
    )

    return [
        {
            "application_id": application.id,
            "job_offer_id": application.job_offer_id,
            "seeker_user_id": application.seeker_user_id,
            "consent_given_at": application.consent_given_at,
            "applied_at": application.created_at,
            "shared_profile": {
                "full_name": snapshot.full_name,
                "summary": snapshot.summary,
                "location": snapshot.location,
                "occupation_key": snapshot.occupation_key,
                "competencies": snapshot.competencies,
            },
            "audit_metadata": snapshot.audit_metadata,
            "snapshot_created_at": snapshot.created_at,
            "shared_matching": (
                _build_shared_matching_for_recruiter(
                    matching_snapshot=matching_snapshot,
                )
                if matching_snapshot is not None
                else None
            ),
        }
        for application, snapshot, matching_snapshot in rows
    ]
