from importlib import import_module

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.db.models import User, UserRole


def assert_error_response(response, *, status_code: int, error: str, message: str) -> None:
    assert response.status_code == status_code

    body = response.json()
    assert body["error"] == error
    assert body["details"]
    assert body["details"][0]["message"] == message


def assert_auth_payload(body: dict, *, email: str, role: str) -> None:
    assert body["access_token"]
    assert body["token_type"] == "bearer"

    user_data = body["user"]
    assert user_data["email"] == email
    assert user_data["role"] == role
    assert isinstance(user_data["id"], int)
    assert user_data["created_at"]


def register_user(client: TestClient, *, email: str, password: str, role: str):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password, "role": role},
    )


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
    response = client.get("/health")

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

    first_response = client.post("/auth/register", json=payload)
    assert first_response.status_code in (200, 201)

    second_response = client.post("/auth/register", json=payload)

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
    response = client.post("/auth/register", json=payload)

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

    response = client.post(
        "/auth/login",
        json={"email": "login-success@example.com", "password": "StrongPassword123!"},
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

    response = client.post("/auth/login", json=payload)

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
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "me@example.com"
    assert body["role"] == "job_seeker"


def test_get_me_missing_token_returns_unauthorized(client):
    response = client.get("/auth/me")

    assert_error_response(
        response,
        status_code=401,
        error="http_error",
        message="Could not validate credentials.",
    )


def test_get_me_malformed_token_returns_unauthorized(client):
    response = client.get(
        "/auth/me",
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
        "/auth/me",
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
        "/auth/me",
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
