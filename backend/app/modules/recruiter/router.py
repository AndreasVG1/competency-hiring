from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.sqlite import get_db_session
from app.modules.auth.dependencies import require_recruiter
from app.modules.recruiter.schemas import (
    JobOfferCreateRequest,
    JobOfferRequirementCreateRequest,
    JobOfferRequirementResponse,
    JobOfferRequirementUpdateRequest,
    JobOfferResponse,
    JobOfferUpdateRequest,
    RecruiterProfileResponse,
    RecruiterProfileUpsertRequest,
)
from app.modules.recruiter.service import (
    add_requirement_to_job_offer,
    create_job_offer_for_user,
    delete_requirement,
    get_owned_job_offer_or_404,
    get_profile_or_404,
    list_job_offers_for_user,
    list_requirements_for_job_offer,
    update_job_offer_for_user,
    update_requirement_priority,
    upsert_profile,
)

router = APIRouter(prefix="/recruiter", tags=["recruiter"])

DbSession = Annotated[Session, Depends(get_db_session)]
CurrentRecruiter = Annotated[User, Depends(require_recruiter)]


@router.get("/profile", response_model=RecruiterProfileResponse)
def read_profile(
    db_session: DbSession,
    current_recruiter: CurrentRecruiter,
) -> RecruiterProfileResponse:
    profile = get_profile_or_404(db_session, user_id=current_recruiter.id)
    return RecruiterProfileResponse.model_validate(profile)


@router.put("/profile", response_model=RecruiterProfileResponse)
def upsert_recruiter_profile(
    payload: RecruiterProfileUpsertRequest,
    db_session: DbSession,
    current_recruiter: CurrentRecruiter,
) -> RecruiterProfileResponse:
    profile = upsert_profile(
        db_session,
        user_id=current_recruiter.id,
        company_name=payload.company_name,
        contact_name=payload.contact_name,
    )
    return RecruiterProfileResponse.model_validate(profile)


@router.get("/job-offers", response_model=list[JobOfferResponse])
def list_job_offers(
    db_session: DbSession,
    current_recruiter: CurrentRecruiter,
) -> list[JobOfferResponse]:
    return [
        JobOfferResponse.model_validate(item)
        for item in list_job_offers_for_user(db_session, user_id=current_recruiter.id)
    ]


@router.post("/job-offers", response_model=JobOfferResponse, status_code=status.HTTP_201_CREATED)
def create_job_offer(
    payload: JobOfferCreateRequest,
    db_session: DbSession,
    current_recruiter: CurrentRecruiter,
) -> JobOfferResponse:
    job_offer = create_job_offer_for_user(
        db_session,
        user_id=current_recruiter.id,
        title=payload.title,
        description=payload.description,
    )
    return JobOfferResponse.model_validate(job_offer)


@router.get("/job-offers/{job_offer_id}", response_model=JobOfferResponse)
def read_job_offer(
    job_offer_id: int,
    db_session: DbSession,
    current_recruiter: CurrentRecruiter,
) -> JobOfferResponse:
    job_offer = get_owned_job_offer_or_404(
        db_session,
        user_id=current_recruiter.id,
        job_offer_id=job_offer_id,
    )
    return JobOfferResponse.model_validate(job_offer)


@router.patch("/job-offers/{job_offer_id}", response_model=JobOfferResponse)
def patch_job_offer(
    job_offer_id: int,
    payload: JobOfferUpdateRequest,
    db_session: DbSession,
    current_recruiter: CurrentRecruiter,
) -> JobOfferResponse:
    job_offer = update_job_offer_for_user(
        db_session,
        user_id=current_recruiter.id,
        job_offer_id=job_offer_id,
        title=payload.title,
        description=payload.description,
    )
    return JobOfferResponse.model_validate(job_offer)


@router.get(
    "/job-offers/{job_offer_id}/requirements",
    response_model=list[JobOfferRequirementResponse],
)
def list_job_offer_requirements(
    job_offer_id: int,
    db_session: DbSession,
    current_recruiter: CurrentRecruiter,
) -> list[JobOfferRequirementResponse]:
    return [
        JobOfferRequirementResponse.model_validate(item)
        for item in list_requirements_for_job_offer(
            db_session,
            user_id=current_recruiter.id,
            job_offer_id=job_offer_id,
        )
    ]


@router.post(
    "/job-offers/{job_offer_id}/requirements",
    response_model=JobOfferRequirementResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_job_offer_requirement(
    job_offer_id: int,
    payload: JobOfferRequirementCreateRequest,
    db_session: DbSession,
    current_recruiter: CurrentRecruiter,
) -> JobOfferRequirementResponse:
    requirement = add_requirement_to_job_offer(
        db_session,
        user_id=current_recruiter.id,
        job_offer_id=job_offer_id,
        competency_key=payload.competency_key,
        priority=payload.priority,
    )
    return JobOfferRequirementResponse.model_validate(requirement)


@router.patch(
    "/job-offers/{job_offer_id}/requirements/{requirement_id}",
    response_model=JobOfferRequirementResponse,
)
def patch_job_offer_requirement(
    job_offer_id: int,
    requirement_id: int,
    payload: JobOfferRequirementUpdateRequest,
    db_session: DbSession,
    current_recruiter: CurrentRecruiter,
) -> JobOfferRequirementResponse:
    requirement = update_requirement_priority(
        db_session,
        user_id=current_recruiter.id,
        job_offer_id=job_offer_id,
        requirement_id=requirement_id,
        priority=payload.priority,
    )
    return JobOfferRequirementResponse.model_validate(requirement)


@router.delete(
    "/job-offers/{job_offer_id}/requirements/{requirement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_job_offer_requirement(
    job_offer_id: int,
    requirement_id: int,
    db_session: DbSession,
    current_recruiter: CurrentRecruiter,
) -> Response:
    delete_requirement(
        db_session,
        user_id=current_recruiter.id,
        job_offer_id=job_offer_id,
        requirement_id=requirement_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
