from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.settings import get_settings

PASSWORD_CONTEXT = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return PASSWORD_CONTEXT.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return PASSWORD_CONTEXT.verify(plain_password, password_hash)


def create_access_token(
    *,
    subject: str,
    role: str | None = None,
    expires_delta_seconds: int | None = None,
) -> str:
    settings = get_settings()
    expires_in_seconds = expires_delta_seconds
    if expires_in_seconds is None:
        expires_in_seconds = settings.jwt_access_token_expire_minutes * 60

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
    payload: dict[str, str | datetime] = {
        "sub": subject,
        "exp": expires_at,
    }
    if role is not None:
        payload["role"] = role

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, object]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )


def get_token_subject(token: str) -> str:
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise ValueError("Invalid token.") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Invalid token.")

    return subject
