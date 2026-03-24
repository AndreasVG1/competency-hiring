from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.sqlite import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import (
    AuthTokenResponse,
    AuthenticatedUser,
    LoginRequest,
    RegisterRequest,
)
from app.modules.auth.security import create_access_token
from app.modules.auth.service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def build_auth_response(user: CurrentUser) -> AuthTokenResponse:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return AuthTokenResponse(
        access_token=token,
        user=AuthenticatedUser.model_validate(user),
    )


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, db_session: DbSession) -> AuthTokenResponse:
    user = register_user(
        db_session,
        email=payload.email,
        password=payload.password,
        role=payload.role,
    )
    return build_auth_response(user)


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest, db_session: DbSession) -> AuthTokenResponse:
    user = authenticate_user(
        db_session,
        email=payload.email,
        password=payload.password,
    )
    return build_auth_response(user)


@router.get("/me", response_model=AuthenticatedUser)
def get_me(current_user: CurrentUser) -> AuthenticatedUser:
    return AuthenticatedUser.model_validate(current_user)
