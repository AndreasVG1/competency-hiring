from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import (
    JobOffer,
    JobOfferRequirement,
    JobOfferStatus,
    RecruiterProfile,
    RequirementPriority,
)
from app.modules.catalog.service import (
    get_competency_detail,
    get_occupation_detail,
    resolve_competencies as resolve_catalog_competencies,
)

PROFILE_NOT_FOUND_MESSAGE = "Recruiter profile not found."
JOB_OFFER_NOT_FOUND_MESSAGE = "Job offer not found."
REQUIREMENT_NOT_FOUND_MESSAGE = "Job offer requirement not found."
DUPLICATE_REQUIREMENT_MESSAGE = "Requirement already exists for this job offer."
INVALID_STATUS_TRANSITION_MESSAGE = "Invalid job offer status transition."

ALLOWED_STATUS_TRANSITIONS: dict[JobOfferStatus, set[JobOfferStatus]] = {
    JobOfferStatus.DRAFT: {JobOfferStatus.PUBLISHED},
    JobOfferStatus.PUBLISHED: {JobOfferStatus.ARCHIVED},
    JobOfferStatus.ARCHIVED: set(),
}


def _validate_competency_key(*, competency_key: str) -> None:
    get_competency_detail(competency_key=competency_key)


def _resolve_occupation_label(*, occupation_key: str) -> str:
    occupation = get_occupation_detail(occupation_key=occupation_key)
    return occupation["label"]


def get_profile_for_user(db_session: Session, *, user_id: int) -> RecruiterProfile | None:
    return (
        db_session.query(RecruiterProfile)
        .filter(RecruiterProfile.user_id == user_id)
        .one_or_none()
    )


def get_profile_or_404(db_session: Session, *, user_id: int) -> RecruiterProfile:
    profile = get_profile_for_user(db_session, user_id=user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PROFILE_NOT_FOUND_MESSAGE,
        )
    return profile


def upsert_profile(
    db_session: Session,
    *,
    user_id: int,
    company_name: str,
    contact_name: str,
) -> RecruiterProfile:
    profile = get_profile_for_user(db_session, user_id=user_id)
    if profile is None:
        profile = RecruiterProfile(
            user_id=user_id,
            company_name=company_name,
            contact_name=contact_name,
        )
        db_session.add(profile)
    else:
        profile.company_name = company_name
        profile.contact_name = contact_name

    db_session.commit()
    db_session.refresh(profile)
    return profile


def list_job_offers_for_user(db_session: Session, *, user_id: int) -> list[JobOffer]:
    return (
        db_session.query(JobOffer)
        .filter(JobOffer.recruiter_user_id == user_id)
        .order_by(JobOffer.id.asc())
        .all()
    )


def create_job_offer_for_user(
    db_session: Session,
    *,
    user_id: int,
    occupation_key: str,
    description: str,
) -> JobOffer:
    occupation_label = _resolve_occupation_label(occupation_key=occupation_key)

    job_offer = JobOffer(
        recruiter_user_id=user_id,
        title=occupation_label,
        occupation_key=occupation_key,
        description=description,
        status=JobOfferStatus.DRAFT,
    )
    db_session.add(job_offer)
    db_session.commit()
    db_session.refresh(job_offer)
    return job_offer


def get_owned_job_offer_or_404(
    db_session: Session,
    *,
    user_id: int,
    job_offer_id: int,
) -> JobOffer:
    job_offer = (
        db_session.query(JobOffer)
        .filter(
            JobOffer.id == job_offer_id,
            JobOffer.recruiter_user_id == user_id,
        )
        .one_or_none()
    )
    if job_offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=JOB_OFFER_NOT_FOUND_MESSAGE,
        )
    return job_offer


def update_job_offer_for_user(
    db_session: Session,
    *,
    user_id: int,
    job_offer_id: int,
    occupation_key: str | None,
    description: str | None,
) -> JobOffer:
    job_offer = get_owned_job_offer_or_404(
        db_session,
        user_id=user_id,
        job_offer_id=job_offer_id,
    )

    if occupation_key is not None:
        job_offer.occupation_key = occupation_key
        job_offer.title = _resolve_occupation_label(occupation_key=occupation_key)
    if description is not None:
        job_offer.description = description

    db_session.commit()
    db_session.refresh(job_offer)
    return job_offer


def delete_job_offer_for_user(
    db_session: Session,
    *,
    user_id: int,
    job_offer_id: int,
) -> None:
    job_offer = get_owned_job_offer_or_404(
        db_session,
        user_id=user_id,
        job_offer_id=job_offer_id,
    )
    db_session.delete(job_offer)
    db_session.commit()


def _transition_job_offer_status(
    db_session: Session,
    *,
    user_id: int,
    job_offer_id: int,
    target_status: JobOfferStatus,
) -> JobOffer:
    job_offer = get_owned_job_offer_or_404(
        db_session,
        user_id=user_id,
        job_offer_id=job_offer_id,
    )

    current_status = job_offer.status
    if target_status not in ALLOWED_STATUS_TRANSITIONS[current_status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{INVALID_STATUS_TRANSITION_MESSAGE} {current_status.value} -> {target_status.value}.",
        )

    job_offer.status = target_status
    db_session.commit()
    db_session.refresh(job_offer)
    return job_offer


def publish_job_offer_for_user(
    db_session: Session,
    *,
    user_id: int,
    job_offer_id: int,
) -> JobOffer:
    return _transition_job_offer_status(
        db_session,
        user_id=user_id,
        job_offer_id=job_offer_id,
        target_status=JobOfferStatus.PUBLISHED,
    )


def archive_job_offer_for_user(
    db_session: Session,
    *,
    user_id: int,
    job_offer_id: int,
) -> JobOffer:
    return _transition_job_offer_status(
        db_session,
        user_id=user_id,
        job_offer_id=job_offer_id,
        target_status=JobOfferStatus.ARCHIVED,
    )


def list_requirements_for_job_offer(
    db_session: Session,
    *,
    user_id: int,
    job_offer_id: int,
) -> list[JobOfferRequirement]:
    get_owned_job_offer_or_404(
        db_session,
        user_id=user_id,
        job_offer_id=job_offer_id,
    )
    return (
        db_session.query(JobOfferRequirement)
        .filter(JobOfferRequirement.job_offer_id == job_offer_id)
        .order_by(JobOfferRequirement.id.asc())
        .all()
    )


def list_requirements_for_job_offer_enriched(
    db_session: Session,
    *,
    user_id: int,
    job_offer_id: int,
) -> list[dict[str, object]]:
    requirements = list_requirements_for_job_offer(
        db_session,
        user_id=user_id,
        job_offer_id=job_offer_id,
    )
    competency_keys = [item.competency_key for item in requirements]

    try:
        resolved = resolve_catalog_competencies(keys=competency_keys)
    except Exception:
        resolved = {"items": [], "missing_keys": competency_keys}
    meta_by_key: dict[str, dict[str, object]] = {
        str(item["key"]): item for item in (resolved.get("items") or []) if item.get("key")
    }

    enriched: list[dict[str, object]] = []
    for item in requirements:
        meta = meta_by_key.get(item.competency_key)
        enriched.append(
            {
                "id": item.id,
                "job_offer_id": item.job_offer_id,
                "competency_key": item.competency_key,
                "priority": item.priority,
                "competency_label": meta.get("label") if meta else None,
                "activity_indicator_count": meta.get("activity_indicator_count") if meta else None,
            }
        )

    return enriched


def add_requirement_to_job_offer(
    db_session: Session,
    *,
    user_id: int,
    job_offer_id: int,
    competency_key: str,
    priority: RequirementPriority,
) -> JobOfferRequirement:
    get_owned_job_offer_or_404(
        db_session,
        user_id=user_id,
        job_offer_id=job_offer_id,
    )
    _validate_competency_key(competency_key=competency_key)

    existing = (
        db_session.query(JobOfferRequirement)
        .filter(
            JobOfferRequirement.job_offer_id == job_offer_id,
            JobOfferRequirement.competency_key == competency_key,
        )
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_REQUIREMENT_MESSAGE,
        )

    requirement = JobOfferRequirement(
        job_offer_id=job_offer_id,
        competency_key=competency_key,
        priority=priority,
    )
    db_session.add(requirement)
    db_session.commit()
    db_session.refresh(requirement)
    return requirement


def get_owned_requirement_or_404(
    db_session: Session,
    *,
    user_id: int,
    job_offer_id: int,
    requirement_id: int,
) -> JobOfferRequirement:
    get_owned_job_offer_or_404(
        db_session,
        user_id=user_id,
        job_offer_id=job_offer_id,
    )

    requirement = (
        db_session.query(JobOfferRequirement)
        .filter(
            JobOfferRequirement.id == requirement_id,
            JobOfferRequirement.job_offer_id == job_offer_id,
        )
        .one_or_none()
    )
    if requirement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=REQUIREMENT_NOT_FOUND_MESSAGE,
        )

    return requirement


def update_requirement_priority(
    db_session: Session,
    *,
    user_id: int,
    job_offer_id: int,
    requirement_id: int,
    priority: RequirementPriority,
) -> JobOfferRequirement:
    requirement = get_owned_requirement_or_404(
        db_session,
        user_id=user_id,
        job_offer_id=job_offer_id,
        requirement_id=requirement_id,
    )
    requirement.priority = priority
    db_session.commit()
    db_session.refresh(requirement)
    return requirement


def delete_requirement(
    db_session: Session,
    *,
    user_id: int,
    job_offer_id: int,
    requirement_id: int,
) -> None:
    requirement = get_owned_requirement_or_404(
        db_session,
        user_id=user_id,
        job_offer_id=job_offer_id,
        requirement_id=requirement_id,
    )
    db_session.delete(requirement)
    db_session.commit()
