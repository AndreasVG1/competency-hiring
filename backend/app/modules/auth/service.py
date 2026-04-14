from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.models import RefreshTokenSession, User, UserRole
from app.modules.auth import security

INVALID_CREDENTIALS_MESSAGE = "Invalid email or password."
DUPLICATE_EMAIL_MESSAGE = "Email is already registered."
INVALID_REFRESH_TOKEN_MESSAGE = "Invalid refresh token."
PASSWORD_REUSE_MESSAGE = "New password must be different from old password."


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db_session: Session, email: str) -> User | None:
    normalized_email = normalize_email(email)
    return db_session.query(User).filter(User.email == normalized_email).one_or_none()


def get_user_by_id(db_session: Session, user_id: int) -> User | None:
    return db_session.query(User).filter(User.id == user_id).one_or_none()


def register_user(
    db_session: Session,
    *,
    email: str,
    password: str,
    role: UserRole,
) -> User:
    normalized_email = normalize_email(email)

    if get_user_by_email(db_session, normalized_email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_EMAIL_MESSAGE,
        )

    user = User(
        email=normalized_email,
        password_hash=security.hash_password(password),
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def authenticate_user(db_session: Session, *, email: str, password: str) -> User:
    user = get_user_by_email(db_session, email)
    if user is None or not security.verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_MESSAGE,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _refresh_token_expires_at() -> datetime:
    settings = get_settings()
    return _utc_now() + timedelta(days=settings.jwt_refresh_token_expire_days)


def _create_refresh_token_session(
    db_session: Session,
    *,
    user_id: int,
) -> str:
    refresh_token = security.create_refresh_token()
    session = RefreshTokenSession(
        user_id=user_id,
        token_hash=security.hash_refresh_token(refresh_token),
        expires_at=_refresh_token_expires_at(),
    )
    db_session.add(session)
    return refresh_token


def issue_auth_tokens(db_session: Session, *, user: User) -> tuple[str, str]:
    access_token = security.create_access_token(subject=str(user.id), role=user.role.value)
    refresh_token = _create_refresh_token_session(db_session, user_id=user.id)
    db_session.commit()
    return access_token, refresh_token


def _get_refresh_token_session(
    db_session: Session,
    *,
    refresh_token: str,
) -> RefreshTokenSession | None:
    token_hash = security.hash_refresh_token(refresh_token)
    statement = select(RefreshTokenSession).where(RefreshTokenSession.token_hash == token_hash)
    return db_session.execute(statement).scalar_one_or_none()


def _require_active_refresh_token_session(
    db_session: Session,
    *,
    refresh_token: str,
) -> RefreshTokenSession:
    session = _get_refresh_token_session(db_session, refresh_token=refresh_token)
    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at <= _utc_now()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_REFRESH_TOKEN_MESSAGE,
        )
    return session


def rotate_refresh_token(db_session: Session, *, refresh_token: str) -> tuple[User, str, str]:
    session = _require_active_refresh_token_session(db_session, refresh_token=refresh_token)
    session.revoked_at = _utc_now()
    access_token = security.create_access_token(
        subject=str(session.user_id),
        role=session.user.role.value,
    )
    new_refresh_token = _create_refresh_token_session(db_session, user_id=session.user_id)
    db_session.commit()
    return session.user, access_token, new_refresh_token


def revoke_refresh_token(db_session: Session, *, refresh_token: str) -> None:
    session = _get_refresh_token_session(db_session, refresh_token=refresh_token)
    if session is not None and session.revoked_at is None and session.expires_at > _utc_now():
        session.revoked_at = _utc_now()
        db_session.commit()


def revoke_all_user_refresh_tokens(db_session: Session, *, user_id: int) -> None:
    statement = select(RefreshTokenSession).where(RefreshTokenSession.user_id == user_id)
    refresh_sessions = db_session.execute(statement).scalars().all()
    now = _utc_now()
    has_changes = False
    for refresh_session in refresh_sessions:
        if refresh_session.revoked_at is None:
            refresh_session.revoked_at = now
            has_changes = True

    if has_changes:
        db_session.commit()


def change_password(
    db_session: Session,
    *,
    user: User,
    old_password: str,
    new_password: str,
) -> None:
    if not security.verify_password(old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_MESSAGE,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if security.verify_password(new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=PASSWORD_REUSE_MESSAGE,
        )

    user.password_hash = security.hash_password(new_password)
    db_session.commit()
    revoke_all_user_refresh_tokens(db_session, user_id=user.id)


def delete_account(
    db_session: Session,
    *,
    user: User,
    current_password: str,
) -> None:
    if not security.verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_MESSAGE,
            headers={"WWW-Authenticate": "Bearer"},
        )

    db_session.delete(user)
    db_session.commit()
