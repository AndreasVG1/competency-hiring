from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.models import User, UserRole
from app.db.sqlite import get_db_session
from app.modules.auth.security import get_token_subject
from app.modules.auth.service import get_user_by_id

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)
FORBIDDEN_EXCEPTION = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="You do not have permission to access this resource.",
)

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db_session)]
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


def get_current_user(
    credentials: BearerCredentials,
    db_session: DbSession,
) -> User:
    if credentials is None:
        raise CREDENTIALS_EXCEPTION

    try:
        subject = get_token_subject(credentials.credentials)
        user_id = int(subject)
    except (TypeError, ValueError):
        raise CREDENTIALS_EXCEPTION

    user = get_user_by_id(db_session, user_id)
    if user is None:
        raise CREDENTIALS_EXCEPTION

    return user


def require_role(required_role: UserRole) -> Callable[[User], User]:
    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role != required_role:
            raise FORBIDDEN_EXCEPTION
        return current_user

    return dependency


require_job_seeker = require_role(UserRole.JOB_SEEKER)
require_recruiter = require_role(UserRole.RECRUITER)
