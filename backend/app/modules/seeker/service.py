from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.db.models import (
    Application,
    CompetencyLevel,
    JobOffer,
    JobOfferRequirement,
    JobOfferStatus,
    JobSeekerCompetency,
    JobSeekerProfile,
    RecruiterProfile,
)
from app.modules.catalog.service import (
    get_competency_detail,
    get_occupation_detail,
    resolve_competencies as resolve_catalog_competencies,
)
from app.modules.explanation import build_explanation
from app.modules.matching.service import (
    get_private_analysis_for_seeker as get_private_matching_analysis_for_seeker,
)
from app.modules.seeker.schemas import (
    PrivateJobOfferAnalysisResponse,
    PublicJobOfferDetail,
    PublicJobOfferListItem,
    PublicJobOfferRequirementItem,
)

PROFILE_NOT_FOUND_MESSAGE = "Seeker profile not found."
COMPETENCY_NOT_FOUND_MESSAGE = "Seeker competency not found."
DUPLICATE_COMPETENCY_MESSAGE = "Competency already exists for this seeker."
PUBLISHED_JOB_OFFER_NOT_FOUND_MESSAGE = "Published job offer not found."


def _validate_occupation_key(*, occupation_key: str) -> None:
    get_occupation_detail(occupation_key=occupation_key)


def _validate_competency_key(*, competency_key: str) -> None:
    get_competency_detail(competency_key=competency_key)


def get_profile_for_user(db_session: Session, *, user_id: int) -> JobSeekerProfile | None:
    return (
        db_session.query(JobSeekerProfile)
        .filter(JobSeekerProfile.user_id == user_id)
        .one_or_none()
    )


def get_profile_or_404(db_session: Session, *, user_id: int) -> JobSeekerProfile:
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
    full_name: str,
    summary: str | None,
    location: str | None,
    occupation_key: str | None,
) -> JobSeekerProfile:
    if occupation_key is not None:
        _validate_occupation_key(occupation_key=occupation_key)

    profile = get_profile_for_user(db_session, user_id=user_id)
    if profile is None:
        profile = JobSeekerProfile(
            user_id=user_id,
            full_name=full_name,
            summary=summary,
            location=location,
            occupation_key=occupation_key,
        )
        db_session.add(profile)
    else:
        profile.full_name = full_name
        profile.summary = summary
        profile.location = location
        profile.occupation_key = occupation_key

    db_session.commit()
    db_session.refresh(profile)
    return profile


def list_competencies_for_user(
    db_session: Session,
    *,
    user_id: int,
) -> list[JobSeekerCompetency]:
    return (
        db_session.query(JobSeekerCompetency)
        .filter(JobSeekerCompetency.user_id == user_id)
        .order_by(JobSeekerCompetency.id.asc())
        .all()
    )


def list_competencies_for_user_enriched(
    db_session: Session,
    *,
    user_id: int,
) -> list[dict[str, object]]:
    competencies = list_competencies_for_user(db_session, user_id=user_id)
    competency_keys = [item.competency_key for item in competencies]

    try:
        resolved = resolve_catalog_competencies(keys=competency_keys)
    except Exception:
        resolved = {"items": [], "missing_keys": competency_keys}
    meta_by_key: dict[str, dict[str, object]] = {
        str(item["key"]): item for item in (resolved.get("items") or []) if item.get("key")
    }

    enriched: list[dict[str, object]] = []
    for item in competencies:
        meta = meta_by_key.get(item.competency_key)
        enriched.append(
            {
                "id": item.id,
                "competency_key": item.competency_key,
                "level": item.level,
                "competency_label": meta.get("label") if meta else None,
                "activity_indicator_count": meta.get("activity_indicator_count") if meta else None,
            }
        )

    return enriched


def add_competency_for_user(
    db_session: Session,
    *,
    user_id: int,
    competency_key: str,
    level: CompetencyLevel,
) -> JobSeekerCompetency:
    _validate_competency_key(competency_key=competency_key)

    existing = (
        db_session.query(JobSeekerCompetency)
        .filter(
            JobSeekerCompetency.user_id == user_id,
            JobSeekerCompetency.competency_key == competency_key,
        )
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_COMPETENCY_MESSAGE,
        )

    competency = JobSeekerCompetency(
        user_id=user_id,
        competency_key=competency_key,
        level=level,
    )
    db_session.add(competency)
    db_session.commit()
    db_session.refresh(competency)
    return competency


def update_competency_level_for_user(
    db_session: Session,
    *,
    user_id: int,
    competency_id: int,
    level: CompetencyLevel,
) -> JobSeekerCompetency:
    competency = (
        db_session.query(JobSeekerCompetency)
        .filter(
            JobSeekerCompetency.id == competency_id,
            JobSeekerCompetency.user_id == user_id,
        )
        .one_or_none()
    )
    if competency is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=COMPETENCY_NOT_FOUND_MESSAGE,
        )

    competency.level = level
    db_session.commit()
    db_session.refresh(competency)
    return competency


def delete_competency_for_user(
    db_session: Session,
    *,
    user_id: int,
    competency_id: int,
) -> None:
    competency = (
        db_session.query(JobSeekerCompetency)
        .filter(
            JobSeekerCompetency.id == competency_id,
            JobSeekerCompetency.user_id == user_id,
        )
        .one_or_none()
    )
    if competency is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=COMPETENCY_NOT_FOUND_MESSAGE,
        )

    db_session.delete(competency)
    db_session.commit()


def delete_profile_for_user(
    db_session: Session,
    *,
    user_id: int,
) -> None:
    profile = get_profile_or_404(db_session, user_id=user_id)

    (
        db_session.query(JobSeekerCompetency)
        .filter(JobSeekerCompetency.user_id == user_id)
        .delete(synchronize_session=False)
    )
    db_session.delete(profile)
    db_session.commit()


def _build_short_description(*, description: str, max_length: int = 160) -> str:
    normalized = " ".join(description.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def list_published_job_offers(
    db_session: Session,
    *,
    seeker_user_id: int,
    query: str | None,
    occupation_key: str | None,
    applied: bool | None,
    limit: int,
    offset: int,
) -> list[PublicJobOfferListItem]:
    statement = (
        db_session.query(
            JobOffer,
            RecruiterProfile.company_name,
            Application.id.label("application_id"),
        )
        .outerjoin(RecruiterProfile, RecruiterProfile.user_id == JobOffer.recruiter_user_id)
        .outerjoin(
            Application,
            and_(
                Application.job_offer_id == JobOffer.id,
                Application.seeker_user_id == seeker_user_id,
            ),
        )
        .filter(JobOffer.status == JobOfferStatus.PUBLISHED)
    )

    normalized_query = query.strip() if query else None
    if normalized_query:
        pattern = f"%{normalized_query}%"
        statement = statement.filter(
            or_(
                JobOffer.title.ilike(pattern),
                JobOffer.description.ilike(pattern),
            )
        )

    normalized_occupation_key = occupation_key.strip() if occupation_key else None
    if normalized_occupation_key:
        statement = statement.filter(JobOffer.occupation_key == normalized_occupation_key)

    if applied is True:
        statement = statement.filter(Application.id.isnot(None))
    elif applied is False:
        statement = statement.filter(Application.id.is_(None))

    rows = (
        statement.order_by(JobOffer.updated_at.desc(), JobOffer.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        PublicJobOfferListItem(
            id=job_offer.id,
            title=job_offer.title,
            occupation_key=job_offer.occupation_key,
            occupation_label=job_offer.title,
            short_description=_build_short_description(description=job_offer.description),
            company_name=company_name or "",
            published_at=job_offer.updated_at,
            applied=application_id is not None,
            application_id=application_id,
        )
        for job_offer, company_name, application_id in rows
    ]


def get_published_job_offer_detail_or_404(
    db_session: Session,
    *,
    seeker_user_id: int,
    job_offer_id: int,
) -> PublicJobOfferDetail:
    row = (
        db_session.query(
            JobOffer,
            RecruiterProfile.company_name,
            Application.id.label("application_id"),
        )
        .outerjoin(RecruiterProfile, RecruiterProfile.user_id == JobOffer.recruiter_user_id)
        .outerjoin(
            Application,
            and_(
                Application.job_offer_id == JobOffer.id,
                Application.seeker_user_id == seeker_user_id,
            ),
        )
        .filter(
            JobOffer.id == job_offer_id,
            JobOffer.status == JobOfferStatus.PUBLISHED,
        )
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PUBLISHED_JOB_OFFER_NOT_FOUND_MESSAGE,
        )

    job_offer, company_name, application_id = row
    requirements = (
        db_session.query(JobOfferRequirement)
        .filter(JobOfferRequirement.job_offer_id == job_offer.id)
        .order_by(JobOfferRequirement.id.asc())
        .all()
    )

    requirement_keys = [requirement.competency_key for requirement in requirements]
    try:
        resolved = resolve_catalog_competencies(keys=requirement_keys)
    except Exception:
        resolved = {"items": [], "missing_keys": requirement_keys}
    meta_by_key: dict[str, dict[str, object]] = {
        str(item["key"]): item for item in (resolved.get("items") or []) if item.get("key")
    }

    return PublicJobOfferDetail(
        id=job_offer.id,
        title=job_offer.title,
        occupation_key=job_offer.occupation_key,
        occupation_label=job_offer.title,
        description=job_offer.description,
        company_name=company_name or "",
        published_at=job_offer.updated_at,
        applied=application_id is not None,
        application_id=application_id,
        requirements=[
            PublicJobOfferRequirementItem(
                competency_key=requirement.competency_key,
                priority=requirement.priority,
                competency_label=(
                    meta_by_key.get(requirement.competency_key, {}).get("label") if requirement.competency_key else None
                ), # type: ignore
                activity_indicator_count=(
                    meta_by_key.get(requirement.competency_key, {}).get("activity_indicator_count")
                    if requirement.competency_key
                    else None
                ), # type: ignore
            )
            for requirement in requirements
        ],
    )


def get_private_job_offer_analysis_with_explanation(
    db_session: Session,
    *,
    seeker_user_id: int,
    job_offer_id: int,
) -> PrivateJobOfferAnalysisResponse:
    matching_result = get_private_matching_analysis_for_seeker(
        db_session,
        seeker_user_id=seeker_user_id,
        job_offer_id=job_offer_id,
    )
    explanation = build_explanation(matching_result, "seeker")
    return PrivateJobOfferAnalysisResponse(
        **matching_result.model_dump(mode="python"),
        explanation=explanation,
    )
