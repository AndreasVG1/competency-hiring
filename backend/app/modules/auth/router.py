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
    RefreshTokenRequest,
    RegisterRequest,
)
from app.modules.auth.service import (
    authenticate_user,
    issue_auth_tokens,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]

def build_auth_response(
    *,
    user: User,
    access_token: str,
    refresh_token: str,
) -> AuthTokenResponse:
    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
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
    access_token, refresh_token = issue_auth_tokens(db_session, user=user)
    return build_auth_response(
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest, db_session: DbSession) -> AuthTokenResponse:
    user = authenticate_user(
        db_session,
        email=payload.email,
        password=payload.password,
    )
    access_token, refresh_token = issue_auth_tokens(db_session, user=user)
    return build_auth_response(
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh(payload: RefreshTokenRequest, db_session: DbSession) -> AuthTokenResponse:
    user, access_token, refresh_token = rotate_refresh_token(
        db_session,
        refresh_token=payload.refresh_token,
    )
    return build_auth_response(
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshTokenRequest, db_session: DbSession) -> None:
    revoke_refresh_token(db_session, refresh_token=payload.refresh_token)


@router.get("/me", response_model=AuthenticatedUser)
def get_me(current_user: CurrentUser) -> AuthenticatedUser:
    return AuthenticatedUser.model_validate(current_user)
