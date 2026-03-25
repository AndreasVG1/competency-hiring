from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.sqlite import get_db_session
from app.modules.auth.dependencies import require_job_seeker
from app.modules.seeker.schemas import (
    SeekerCompetencyCreateRequest,
    SeekerCompetencyResponse,
    SeekerCompetencyUpdateRequest,
    SeekerProfileResponse,
    SeekerProfileUpsertRequest,
)
from app.modules.seeker.service import (
    add_competency_for_user,
    delete_competency_for_user,
    get_profile_or_404,
    list_competencies_for_user,
    update_competency_level_for_user,
    upsert_profile,
)

router = APIRouter(prefix="/seeker", tags=["seeker"])

DbSession = Annotated[Session, Depends(get_db_session)]
CurrentSeeker = Annotated[User, Depends(require_job_seeker)]


@router.get("/profile", response_model=SeekerProfileResponse)
def read_profile(db_session: DbSession, current_seeker: CurrentSeeker) -> SeekerProfileResponse:
    profile = get_profile_or_404(db_session, user_id=current_seeker.id)
    return SeekerProfileResponse.model_validate(profile)


@router.put("/profile", response_model=SeekerProfileResponse)
def upsert_seeker_profile(
    payload: SeekerProfileUpsertRequest,
    db_session: DbSession,
    current_seeker: CurrentSeeker,
) -> SeekerProfileResponse:
    profile = upsert_profile(
        db_session,
        user_id=current_seeker.id,
        full_name=payload.full_name,
        summary=payload.summary,
        location=payload.location,
        occupation_key=payload.occupation_key,
    )
    return SeekerProfileResponse.model_validate(profile)


@router.get("/competencies", response_model=list[SeekerCompetencyResponse])
def list_seeker_competencies(
    db_session: DbSession,
    current_seeker: CurrentSeeker,
) -> list[SeekerCompetencyResponse]:
    return [
        SeekerCompetencyResponse.model_validate(item)
        for item in list_competencies_for_user(db_session, user_id=current_seeker.id)
    ]


@router.post(
    "/competencies",
    response_model=SeekerCompetencyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_seeker_competency(
    payload: SeekerCompetencyCreateRequest,
    db_session: DbSession,
    current_seeker: CurrentSeeker,
) -> SeekerCompetencyResponse:
    competency = add_competency_for_user(
        db_session,
        user_id=current_seeker.id,
        competency_key=payload.competency_key,
        level=payload.level,
    )
    return SeekerCompetencyResponse.model_validate(competency)


@router.patch("/competencies/{competency_id}", response_model=SeekerCompetencyResponse)
def patch_seeker_competency(
    competency_id: int,
    payload: SeekerCompetencyUpdateRequest,
    db_session: DbSession,
    current_seeker: CurrentSeeker,
) -> SeekerCompetencyResponse:
    competency = update_competency_level_for_user(
        db_session,
        user_id=current_seeker.id,
        competency_id=competency_id,
        level=payload.level,
    )
    return SeekerCompetencyResponse.model_validate(competency)


@router.delete("/competencies/{competency_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_seeker_competency(
    competency_id: int,
    db_session: DbSession,
    current_seeker: CurrentSeeker,
) -> Response:
    delete_competency_for_user(
        db_session,
        user_id=current_seeker.id,
        competency_id=competency_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
