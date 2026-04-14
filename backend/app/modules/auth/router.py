from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.sqlite import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import (
    AuthTokenResponse,
    AuthenticatedUser,
    ChangePasswordRequest,
    DeleteAccountRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
)
from app.modules.auth.cookies import (
    clear_auth_cookies,
    get_refresh_token_from_cookie,
    set_auth_cookies,
    validate_csrf_for_refresh_cookie,
)
from app.modules.auth.service import (
    authenticate_user,
    change_password,
    delete_account,
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
def register(
    payload: RegisterRequest,
    db_session: DbSession,
    response: Response,
) -> AuthTokenResponse:
    user = register_user(
        db_session,
        email=payload.email,
        password=payload.password,
        role=payload.role,
    )
    access_token, refresh_token = issue_auth_tokens(db_session, user=user)
    set_auth_cookies(response, refresh_token=refresh_token)
    return build_auth_response(
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest, db_session: DbSession, response: Response) -> AuthTokenResponse:
    user = authenticate_user(
        db_session,
        email=payload.email,
        password=payload.password,
    )
    access_token, refresh_token = issue_auth_tokens(db_session, user=user)
    set_auth_cookies(response, refresh_token=refresh_token)
    return build_auth_response(
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh(
    db_session: DbSession,
    request: Request,
    response: Response,
    payload: RefreshTokenRequest | None = None,
) -> AuthTokenResponse:
    refresh_token = payload.refresh_token if payload else None
    if refresh_token is None:
        refresh_token = get_refresh_token_from_cookie(request)
        if refresh_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )
        validate_csrf_for_refresh_cookie(request, refresh_token=refresh_token)

    user, access_token, refresh_token = rotate_refresh_token(
        db_session,
        refresh_token=refresh_token,
    )
    set_auth_cookies(response, refresh_token=refresh_token)
    return build_auth_response(
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    db_session: DbSession,
    request: Request,
    response: Response,
    payload: RefreshTokenRequest | None = None,
) -> None:
    refresh_token = payload.refresh_token if payload else None
    if refresh_token is None:
        refresh_token = get_refresh_token_from_cookie(request)
        if refresh_token is not None:
            validate_csrf_for_refresh_cookie(request, refresh_token=refresh_token)

    if refresh_token is not None:
        revoke_refresh_token(db_session, refresh_token=refresh_token)

    clear_auth_cookies(response)


@router.get("/me", response_model=AuthenticatedUser)
def get_me(current_user: CurrentUser) -> AuthenticatedUser:
    return AuthenticatedUser.model_validate(current_user)


@router.post("/account/password", status_code=status.HTTP_204_NO_CONTENT)
def update_password(
    payload: ChangePasswordRequest,
    db_session: DbSession,
    response: Response,
    current_user: CurrentUser,
) -> None:
    change_password(
        db_session,
        user=current_user,
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    clear_auth_cookies(response)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def remove_account(
    payload: DeleteAccountRequest,
    db_session: DbSession,
    response: Response,
    current_user: CurrentUser,
) -> None:
    delete_account(
        db_session,
        user=current_user,
        current_password=payload.current_password,
    )
    clear_auth_cookies(response)
