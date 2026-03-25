import hmac
import hashlib

from fastapi import HTTPException, Request, Response, status

from app.core.settings import get_settings

CSRF_HEADER_NAME = "x-csrf-token"


def _csrf_token_for_refresh_token(refresh_token: str) -> str:
    settings = get_settings()
    digest = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        refresh_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


def set_auth_cookies(response: Response, *, refresh_token: str) -> None:
    settings = get_settings()
    csrf_token = _csrf_token_for_refresh_token(refresh_token)
    max_age_seconds = settings.jwt_refresh_token_expire_days * 24 * 60 * 60

    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=refresh_token,
        max_age=max_age_seconds,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite, # type: ignore
        path=settings.auth_cookie_path,
    )
    response.set_cookie(
        key=settings.auth_csrf_cookie_name,
        value=csrf_token,
        max_age=max_age_seconds,
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite, # type: ignore
        path=settings.auth_cookie_path,
    )


def clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        path=settings.auth_cookie_path,
    )
    response.delete_cookie(
        key=settings.auth_csrf_cookie_name,
        path=settings.auth_cookie_path,
    )


def get_refresh_token_from_cookie(request: Request) -> str | None:
    settings = get_settings()
    token = request.cookies.get(settings.auth_refresh_cookie_name)
    if token is None or token.strip() == "":
        return None
    return token


def validate_csrf_for_refresh_cookie(request: Request, *, refresh_token: str) -> None:
    settings = get_settings()
    csrf_cookie_token = request.cookies.get(settings.auth_csrf_cookie_name)
    csrf_header_token = request.headers.get(CSRF_HEADER_NAME)
    expected_csrf_token = _csrf_token_for_refresh_token(refresh_token)

    if (
        csrf_cookie_token is None
        or csrf_header_token is None
        or not hmac.compare_digest(csrf_cookie_token, csrf_header_token)
        or not hmac.compare_digest(expected_csrf_token, csrf_header_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid CSRF token.",
        )
