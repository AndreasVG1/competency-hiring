from importlib import import_module
from datetime import datetime, timezone

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.db.models import (
    Application,
    CompetencyLevel,
    JobOffer,
    JobOfferStatus,
    JobSeekerCompetency,
    JobSeekerProfile,
    RecruiterProfile,
    User,
    UserRole,
)
from app.core.settings import get_settings

API_PREFIX = "/api/v1"
REGISTER_ROUTE = f"{API_PREFIX}/auth/register"
LOGIN_ROUTE = f"{API_PREFIX}/auth/login"
REFRESH_ROUTE = f"{API_PREFIX}/auth/refresh"
LOGOUT_ROUTE = f"{API_PREFIX}/auth/logout"
AUTH_ME_ROUTE = f"{API_PREFIX}/auth/me"
ACCOUNT_PASSWORD_ROUTE = f"{API_PREFIX}/auth/account/password"
ACCOUNT_ROUTE = f"{API_PREFIX}/auth/account"

def assert_error_response(response, *, status_code: int, error: str, message: str) -> None:
    assert response.status_code == status_code

    body = response.json()
    assert body["error"] == error
    assert body["details"]
    assert body["details"][0]["message"] == message


def assert_auth_payload(body: dict, *, email: str, role: str) -> None:
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"

    user_data = body["user"]
    assert user_data["email"] == email
    assert user_data["role"] == role
    assert isinstance(user_data["id"], int)
    assert user_data["created_at"]


def register_user(client: TestClient, *, email: str, password: str, role: str):
    return client.post(
        REGISTER_ROUTE,
        json={"email": email, "password": password, "role": role},
    )


def login_user(client: TestClient, *, email: str, password: str):
    return client.post(
        LOGIN_ROUTE,
        json={"email": email, "password": password},
    )


def csrf_headers_from_cookie(client: TestClient) -> dict[str, str]:
    settings = get_settings()
    csrf_token = client.cookies.get(settings.auth_csrf_cookie_name)
    assert csrf_token
    return {"x-csrf-token": csrf_token}


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def import_or_xfail(module_name: str):
    try:
        return import_module(module_name)
    except ModuleNotFoundError:
        pytest.xfail(f"{module_name} is not implemented yet.")


def build_role_probe_client(app):
    dependencies_module = import_or_xfail("app.modules.auth.dependencies")
    security_module = import_or_xfail("app.modules.auth.security")

    router = APIRouter()

    @router.get("/_test/job-seeker-only")
    def job_seeker_only(_: object = Depends(dependencies_module.require_job_seeker)):
        return {"ok": True}

    @router.get("/_test/recruiter-only")
    def recruiter_only(_: object = Depends(dependencies_module.require_recruiter)):
        return {"ok": True}

    app.include_router(router)

    return TestClient(app), security_module


def create_user(db_session, *, email: str, role: UserRole) -> User:
    user = User(email=email, password_hash="not-a-raw-password", role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_health_endpoint(client):
    response = client.get(API_PREFIX + "/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "service" in body
    assert "environment" in body


@pytest.mark.parametrize("role", ["job_seeker", "recruiter"])
def test_register_returns_auth_payload_for_supported_roles(client, role):
    response = register_user(
        client,
        email=f"{role}@example.com",
        password="StrongPassword123!",
        role=role,
    )

    assert response.status_code in (200, 201)
    assert_auth_payload(response.json(), email=f"{role}@example.com", role=role)


def test_register_stores_password_hash_instead_of_raw_password(client, db_session):
    password = "StrongPassword123!"
    response = register_user(
        client,
        email="hashcheck@example.com",
        password=password,
        role="job_seeker",
    )

    assert response.status_code in (200, 201)

    user = db_session.query(User).filter(User.email == "hashcheck@example.com").one()
    assert user.password_hash
    assert user.password_hash != password


def test_register_duplicate_email_returns_conflict_with_structured_error(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPassword123!",
        "role": "recruiter",
    }

    first_response = client.post(REGISTER_ROUTE, json=payload)
    assert first_response.status_code in (200, 201)

    second_response = client.post(REGISTER_ROUTE, json=payload)

    assert_error_response(
        second_response,
        status_code=409,
        error="http_error",
        message="Email is already registered.",
    )


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"email": "invalid-role@example.com", "password": "StrongPassword123!", "role": "admin"}, "body.role"),
        ({"email": "missing-password@example.com", "role": "job_seeker"}, "body.password"),
    ],
)
def test_register_rejects_invalid_payload_with_validation_error(client, payload, field):
    response = client.post(REGISTER_ROUTE, json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["details"]
    assert body["details"][0]["field"] == field


def test_login_returns_auth_payload_for_valid_credentials(client):
    register_user(
        client,
        email="login-success@example.com",
        password="StrongPassword123!",
        role="job_seeker",
    )

    response = login_user(
        client,
        email="login-success@example.com",
        password="StrongPassword123!",
    )

    assert response.status_code == 200
    assert_auth_payload(
        response.json(),
        email="login-success@example.com",
        role="job_seeker",
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "unknown@example.com", "password": "StrongPassword123!"},
        {"email": "wrong-password@example.com", "password": "wrong-password"},
    ],
)
def test_login_rejects_invalid_credentials_with_generic_message(client, payload):
    register_user(
        client,
        email="wrong-password@example.com",
        password="StrongPassword123!",
        role="job_seeker",
    )

    response = client.post(LOGIN_ROUTE, json=payload)

    assert_error_response(
        response,
        status_code=401,
        error="http_error",
        message="Invalid email or password.",
    )


def test_get_me_returns_authenticated_user_for_valid_token(client):
    register_response = register_user(
        client,
        email="me@example.com",
        password="StrongPassword123!",
        role="job_seeker",
    )
    assert register_response.status_code in (200, 201)

    token = register_response.json()["access_token"]

    response = client.get(
        AUTH_ME_ROUTE,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "me@example.com"
    assert body["role"] == "job_seeker"


def test_get_me_missing_token_returns_unauthorized(client):
    response = client.get(AUTH_ME_ROUTE)

    assert_error_response(
        response,
        status_code=401,
        error="http_error",
        message="Could not validate credentials.",
    )


def test_get_me_malformed_token_returns_unauthorized(client):
    response = client.get(
        AUTH_ME_ROUTE,
        headers={"Authorization": "Bearer definitely-not-a-jwt"},
    )

    assert_error_response(
        response,
        status_code=401,
        error="http_error",
        message="Could not validate credentials.",
    )


def test_get_me_expired_token_returns_unauthorized(client):
    security_module = import_or_xfail("app.modules.auth.security")

    response = client.get(
        AUTH_ME_ROUTE,
        headers={"Authorization": f"Bearer {security_module.create_access_token(subject='1', expires_delta_seconds=-1)}"},
    )

    assert_error_response(
        response,
        status_code=401,
        error="http_error",
        message="Could not validate credentials.",
    )


def test_get_me_missing_user_returns_unauthorized(client):
    security_module = import_or_xfail("app.modules.auth.security")

    response = client.get(
        AUTH_ME_ROUTE,
        headers={"Authorization": f"Bearer {security_module.create_access_token(subject='999999')}"},
    )

    assert_error_response(
        response,
        status_code=401,
        error="http_error",
        message="Could not validate credentials.",
    )


def test_recruiter_token_is_rejected_by_job_seeker_dependency(app, db_session):
    probe_client, _security_module = build_role_probe_client(app)
    user = create_user(
        db_session,
        email="recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    token = _security_module.create_access_token(subject=str(user.id))

    with probe_client:
        response = probe_client.get(
            "/_test/job-seeker-only",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert_error_response(
        response,
        status_code=403,
        error="http_error",
        message="You do not have permission to access this resource.",
    )


def test_job_seeker_token_is_rejected_by_recruiter_dependency(app, db_session):
    probe_client, _security_module = build_role_probe_client(app)
    user = create_user(
        db_session,
        email="seeker@example.com",
        role=UserRole.JOB_SEEKER,
    )
    token = _security_module.create_access_token(subject=str(user.id))

    with probe_client:
        response = probe_client.get(
            "/_test/recruiter-only",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert_error_response(
        response,
        status_code=403,
        error="http_error",
        message="You do not have permission to access this resource.",
    )


def test_refresh_returns_new_token_pair_and_rotates_refresh_token(client):
    register_user(
        client,
        email="refresh-success@example.com",
        password="StrongPassword123!",
        role="job_seeker",
    )
    login_response = login_user(
        client,
        email="refresh-success@example.com",
        password="StrongPassword123!",
    )
    assert login_response.status_code == 200
    issued = login_response.json()

    refresh_response = client.post(
        REFRESH_ROUTE,
        json={"refresh_token": issued["refresh_token"]},
    )

    assert refresh_response.status_code == 200
    body = refresh_response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["refresh_token"] != issued["refresh_token"]
    assert body["user"]["email"] == "refresh-success@example.com"

    reused_response = client.post(
        REFRESH_ROUTE,
        json={"refresh_token": issued["refresh_token"]},
    )
    assert_error_response(
        reused_response,
        status_code=401,
        error="http_error",
        message="Invalid refresh token.",
    )


def test_refresh_rejects_expired_refresh_token(client, db_session):
    auth_service_module = import_or_xfail("app.modules.auth.service")
    refresh_model_module = import_or_xfail("app.db.models")

    register_user(
        client,
        email="refresh-expired@example.com",
        password="StrongPassword123!",
        role="job_seeker",
    )
    login_response = login_user(
        client,
        email="refresh-expired@example.com",
        password="StrongPassword123!",
    )
    refresh_token = login_response.json()["refresh_token"]
    token_hash = auth_service_module.security.hash_refresh_token(refresh_token)
    session = (
        db_session.query(refresh_model_module.RefreshTokenSession)
        .filter(refresh_model_module.RefreshTokenSession.token_hash == token_hash)
        .one()
    )
    session.expires_at = auth_service_module._utc_now() - auth_service_module.timedelta(seconds=1)
    db_session.commit()

    response = client.post(
        REFRESH_ROUTE,
        json={"refresh_token": refresh_token},
    )
    assert_error_response(
        response,
        status_code=401,
        error="http_error",
        message="Invalid refresh token.",
    )


def test_logout_revokes_refresh_token_and_is_idempotent(client):
    register_user(
        client,
        email="logout@example.com",
        password="StrongPassword123!",
        role="job_seeker",
    )
    login_response = login_user(
        client,
        email="logout@example.com",
        password="StrongPassword123!",
    )
    refresh_token = login_response.json()["refresh_token"]

    first_logout = client.post(LOGOUT_ROUTE, json={"refresh_token": refresh_token})
    assert first_logout.status_code == 204

    second_logout = client.post(LOGOUT_ROUTE, json={"refresh_token": refresh_token})
    assert second_logout.status_code == 204

    refresh_after_logout = client.post(
        REFRESH_ROUTE,
        json={"refresh_token": refresh_token},
    )
    assert_error_response(
        refresh_after_logout,
        status_code=401,
        error="http_error",
        message="Invalid refresh token.",
    )


def test_logout_returns_204_for_unknown_refresh_token(client):
    response = client.post(
        LOGOUT_ROUTE,
        json={"refresh_token": "this-token-does-not-exist"},
    )
    assert response.status_code == 204


def test_login_sets_refresh_and_csrf_cookies(client):
    register_user(
        client,
        email="cookie-login@example.com",
        password="StrongPassword123!",
        role="job_seeker",
    )
    response = login_user(
        client,
        email="cookie-login@example.com",
        password="StrongPassword123!",
    )
    assert response.status_code == 200

    settings = get_settings()
    assert client.cookies.get(settings.auth_refresh_cookie_name)
    assert client.cookies.get(settings.auth_csrf_cookie_name)


def test_refresh_accepts_cookie_with_csrf_header(client):
    register_user(
        client,
        email="cookie-refresh@example.com",
        password="StrongPassword123!",
        role="job_seeker",
    )
    login_response = login_user(
        client,
        email="cookie-refresh@example.com",
        password="StrongPassword123!",
    )
    issued_refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post(
        REFRESH_ROUTE,
        headers=csrf_headers_from_cookie(client),
    )
    assert refresh_response.status_code == 200
    rotated_refresh_token = refresh_response.json()["refresh_token"]
    assert rotated_refresh_token != issued_refresh_token

    old_token_reuse = client.post(
        REFRESH_ROUTE,
        json={"refresh_token": issued_refresh_token},
    )
    assert_error_response(
        old_token_reuse,
        status_code=401,
        error="http_error",
        message="Invalid refresh token.",
    )


def test_refresh_with_cookie_requires_csrf_header(client):
    register_user(
        client,
        email="cookie-csrf@example.com",
        password="StrongPassword123!",
        role="job_seeker",
    )
    login_user(
        client,
        email="cookie-csrf@example.com",
        password="StrongPassword123!",
    )

    response = client.post(REFRESH_ROUTE)
    assert_error_response(
        response,
        status_code=403,
        error="http_error",
        message="Missing or invalid CSRF token.",
    )


def test_change_password_updates_credentials_and_revokes_refresh_sessions(client):
    register_response = register_user(
        client,
        email="change-password@example.com",
        password="OldPassword123!",
        role="job_seeker",
    )
    access_token = register_response.json()["access_token"]

    response = client.post(
        ACCOUNT_PASSWORD_ROUTE,
        json={
            "old_password": "OldPassword123!",
            "new_password": "NewPassword123!",
            "confirm_new_password": "NewPassword123!",
        },
        headers=auth_headers(access_token),
    )
    assert response.status_code == 204

    old_login = login_user(
        client,
        email="change-password@example.com",
        password="OldPassword123!",
    )
    assert_error_response(
        old_login,
        status_code=401,
        error="http_error",
        message="Invalid email or password.",
    )

    new_login = login_user(
        client,
        email="change-password@example.com",
        password="NewPassword123!",
    )
    assert new_login.status_code == 200

    refresh_after_change = client.post(
        REFRESH_ROUTE,
        json={"refresh_token": register_response.json()["refresh_token"]},
    )
    assert_error_response(
        refresh_after_change,
        status_code=401,
        error="http_error",
        message="Invalid refresh token.",
    )


def test_change_password_rejects_wrong_old_password(client):
    register_response = register_user(
        client,
        email="wrong-old-password@example.com",
        password="OldPassword123!",
        role="job_seeker",
    )
    access_token = register_response.json()["access_token"]

    response = client.post(
        ACCOUNT_PASSWORD_ROUTE,
        json={
            "old_password": "WrongPassword123!",
            "new_password": "NewPassword123!",
            "confirm_new_password": "NewPassword123!",
        },
        headers=auth_headers(access_token),
    )

    assert_error_response(
        response,
        status_code=401,
        error="http_error",
        message="Invalid email or password.",
    )


def test_change_password_rejects_same_password(client):
    register_response = register_user(
        client,
        email="same-password@example.com",
        password="SamePassword123!",
        role="job_seeker",
    )
    access_token = register_response.json()["access_token"]

    response = client.post(
        ACCOUNT_PASSWORD_ROUTE,
        json={
            "old_password": "SamePassword123!",
            "new_password": "SamePassword123!",
            "confirm_new_password": "SamePassword123!",
        },
        headers=auth_headers(access_token),
    )

    assert_error_response(
        response,
        status_code=400,
        error="http_error",
        message="New password must be different from old password.",
    )


def test_change_password_rejects_confirmation_mismatch(client):
    register_response = register_user(
        client,
        email="password-confirmation@example.com",
        password="OldPassword123!",
        role="job_seeker",
    )
    access_token = register_response.json()["access_token"]

    response = client.post(
        ACCOUNT_PASSWORD_ROUTE,
        json={
            "old_password": "OldPassword123!",
            "new_password": "NewPassword123!",
            "confirm_new_password": "MismatchPassword123!",
        },
        headers=auth_headers(access_token),
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["details"]
    assert body["details"][0]["field"] == "body.confirm_new_password"


def test_change_password_requires_authentication(client):
    response = client.post(
        ACCOUNT_PASSWORD_ROUTE,
        json={
            "old_password": "OldPassword123!",
            "new_password": "NewPassword123!",
            "confirm_new_password": "NewPassword123!",
        },
    )
    assert_error_response(
        response,
        status_code=401,
        error="http_error",
        message="Could not validate credentials.",
    )


def test_change_password_clears_auth_cookies(client):
    register_response = register_user(
        client,
        email="change-password-cookie@example.com",
        password="OldPassword123!",
        role="job_seeker",
    )
    access_token = register_response.json()["access_token"]

    response = client.post(
        ACCOUNT_PASSWORD_ROUTE,
        json={
            "old_password": "OldPassword123!",
            "new_password": "NewPassword123!",
            "confirm_new_password": "NewPassword123!",
        },
        headers=auth_headers(access_token),
    )
    assert response.status_code == 204

    settings = get_settings()
    assert client.cookies.get(settings.auth_refresh_cookie_name) is None
    assert client.cookies.get(settings.auth_csrf_cookie_name) is None


def test_delete_account_hard_deletes_user_and_cascades_rows(client, db_session):
    recruiter = create_user(db_session, email="cascade-recruiter@example.com", role=UserRole.RECRUITER)
    db_session.add(RecruiterProfile(user_id=recruiter.id, company_name="Cascade Ltd", contact_name="Manager"))
    job_offer = JobOffer(
        recruiter_user_id=recruiter.id,
        title="Backend Engineer",
        occupation_key="occupation.backend",
        description="Role",
        status=JobOfferStatus.PUBLISHED,
    )
    db_session.add(job_offer)
    db_session.flush()
    db_session.commit()

    seeker_register_response = register_user(
        client,
        email="cascade-seeker@example.com",
        password="DeleteMe123!",
        role="job_seeker",
    )
    seeker_token = seeker_register_response.json()["access_token"]
    seeker_user = db_session.query(User).filter(User.email == "cascade-seeker@example.com").one()
    seeker_user_id = seeker_user.id

    db_session.add(
        JobSeekerProfile(
            user_id=seeker_user_id,
            full_name="Cascade Seeker",
            summary="Summary",
            location="Tallinn",
            occupation_key="occupation.backend",
        )
    )
    db_session.add(
        JobSeekerCompetency(
            user_id=seeker_user_id,
            competency_key="competency.python",
            level=CompetencyLevel.ADVANCED,
        )
    )
    db_session.add(
        Application(
            job_offer_id=job_offer.id,
            seeker_user_id=seeker_user_id,
            consent_given_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    db_session.commit()

    response = client.request(
        "DELETE",
        ACCOUNT_ROUTE,
        json={"current_password": "DeleteMe123!"},
        headers=auth_headers(seeker_token),
    )
    assert response.status_code == 204
    db_session.expire_all()

    deleted_user = db_session.query(User).filter(User.email == "cascade-seeker@example.com").one_or_none()
    assert deleted_user is None
    assert db_session.query(JobSeekerProfile).filter(JobSeekerProfile.user_id == seeker_user_id).count() == 0
    assert db_session.query(JobSeekerCompetency).filter(JobSeekerCompetency.user_id == seeker_user_id).count() == 0
    assert db_session.query(Application).filter(Application.seeker_user_id == seeker_user_id).count() == 0


@pytest.mark.parametrize("role", ["job_seeker", "recruiter"])
def test_delete_account_works_for_both_roles(client, role):
    password = "DeleteAccount123!"
    register_response = register_user(
        client,
        email=f"delete-{role}@example.com",
        password=password,
        role=role,
    )
    access_token = register_response.json()["access_token"]

    response = client.request(
        "DELETE",
        ACCOUNT_ROUTE,
        json={"current_password": password},
        headers=auth_headers(access_token),
    )

    assert response.status_code == 204


def test_delete_account_rejects_wrong_password(client):
    register_response = register_user(
        client,
        email="delete-wrong-password@example.com",
        password="DeleteMe123!",
        role="job_seeker",
    )
    access_token = register_response.json()["access_token"]

    response = client.request(
        "DELETE",
        ACCOUNT_ROUTE,
        json={"current_password": "WrongPassword123!"},
        headers=auth_headers(access_token),
    )

    assert_error_response(
        response,
        status_code=401,
        error="http_error",
        message="Invalid email or password.",
    )


def test_delete_account_requires_authentication(client):
    response = client.request(
        "DELETE",
        ACCOUNT_ROUTE,
        json={"current_password": "DeleteMe123!"},
    )

    assert_error_response(
        response,
        status_code=401,
        error="http_error",
        message="Could not validate credentials.",
    )


def test_delete_account_clears_auth_cookies(client):
    password = "DeleteCookie123!"
    register_response = register_user(
        client,
        email="delete-cookie@example.com",
        password=password,
        role="job_seeker",
    )
    access_token = register_response.json()["access_token"]

    response = client.request(
        "DELETE",
        ACCOUNT_ROUTE,
        json={"current_password": password},
        headers=auth_headers(access_token),
    )
    assert response.status_code == 204

    settings = get_settings()
    assert client.cookies.get(settings.auth_refresh_cookie_name) is None
    assert client.cookies.get(settings.auth_csrf_cookie_name) is None
