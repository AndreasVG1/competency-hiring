from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import CompetencyLevel, JobSeekerCompetency, JobSeekerProfile
from app.modules.catalog.service import get_competency_detail, get_occupation_detail

PROFILE_NOT_FOUND_MESSAGE = "Seeker profile not found."
COMPETENCY_NOT_FOUND_MESSAGE = "Seeker competency not found."
DUPLICATE_COMPETENCY_MESSAGE = "Competency already exists for this seeker."


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
