from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import User, UserRole
from app.modules.auth import security

INVALID_CREDENTIALS_MESSAGE = "Invalid email or password."
DUPLICATE_EMAIL_MESSAGE = "Email is already registered."


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
