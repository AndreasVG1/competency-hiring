from fastapi import HTTPException
from fastapi.testclient import TestClient

API_PREFIX = "/api/v1"
REGISTER_ROUTE = f"{API_PREFIX}/auth/register"
SEEKER_ROUTE = f"{API_PREFIX}/seeker/profile"
SEEKER_COMPETENCIES_ROUTE = f"{API_PREFIX}/seeker/competencies"

SEEKER_PATHS = [
    ("GET", SEEKER_ROUTE),
    ("PUT", SEEKER_ROUTE),
    ("GET", SEEKER_COMPETENCIES_ROUTE),
    ("POST", SEEKER_COMPETENCIES_ROUTE),
    ("PATCH", f"{SEEKER_COMPETENCIES_ROUTE}/1"),
    ("DELETE", f"{SEEKER_COMPETENCIES_ROUTE}/1"),
]


def assert_structured_http_error(response, *, status_code: int, message: str | None = None) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert body["error"] == "http_error"
    assert body["details"]
    assert "message" in body["details"][0]
    if message is not None:
        assert body["details"][0]["message"] == message


def register_and_get_token(client: TestClient, *, email: str, role: str) -> str:
    response = client.post(
        REGISTER_ROUTE,
        json={"email": email, "password": "StrongPassword123!", "role": role},
    )
    assert response.status_code in (200, 201)
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def call_endpoint(client: TestClient, method: str, path: str, *, token: str | None = None):
    headers = auth_headers(token) if token else None

    json_by_method = {
        "PUT": {
            "full_name": "Alice Example",
            "summary": "Summary",
            "location": "Tallinn",
            "occupation_key": "occ_1",
        },
        "POST": {"competency_key": "comp_1", "level": "beginner"},
        "PATCH": {"level": "advanced"},
    }
    json = json_by_method.get(method)
    return client.request(method, path, headers=headers, json=json)


def test_seeker_endpoints_require_authentication(client: TestClient):
    for method, path in SEEKER_PATHS:
        response = call_endpoint(client, method, path)
        assert_structured_http_error(
            response,
            status_code=401,
            message="Could not validate credentials.",
        )


def test_recruiter_token_is_forbidden_on_seeker_endpoints(client: TestClient):
    token = register_and_get_token(
        client,
        email="recruiter-seeker-api@example.com",
        role="recruiter",
    )

    for method, path in SEEKER_PATHS:
        response = call_endpoint(client, method, path, token=token)
        assert_structured_http_error(
            response,
            status_code=403,
            message="You do not have permission to access this resource.",
        )


def test_profile_get_returns_404_before_creation(client: TestClient):
    token = register_and_get_token(
        client,
        email="seeker-profile-missing@example.com",
        role="job_seeker",
    )

    response = client.get(SEEKER_ROUTE, headers=auth_headers(token))

    assert_structured_http_error(
        response,
        status_code=404,
        message="Seeker profile not found.",
    )


def test_profile_put_creates_profile_when_missing(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="seeker-profile-create@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.seeker.service.get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": "Occupation"},
    )

    response = client.put(
        SEEKER_ROUTE,
        headers=auth_headers(token),
        json={
            "full_name": "Alice Example",
            "summary": "Bio",
            "location": "Tallinn",
            "occupation_key": "occ_1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Alice Example"
    assert body["summary"] == "Bio"
    assert body["location"] == "Tallinn"
    assert body["occupation_key"] == "occ_1"
    assert body["created_at"]
    assert body["updated_at"]


def test_profile_put_updates_existing_profile(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="seeker-profile-update@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.seeker.service.get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": "Occupation"},
    )

    first = client.put(
        SEEKER_ROUTE,
        headers=auth_headers(token),
        json={
            "full_name": "First Name",
            "summary": "First",
            "location": "Tartu",
            "occupation_key": "occ_1",
        },
    )
    assert first.status_code == 200

    second = client.put(
        SEEKER_ROUTE,
        headers=auth_headers(token),
        json={
            "full_name": "Updated Name",
            "summary": "Second",
            "location": "Tallinn",
            "occupation_key": "occ_2",
        },
    )

    assert second.status_code == 200
    body = second.json()
    assert body["full_name"] == "Updated Name"
    assert body["summary"] == "Second"
    assert body["location"] == "Tallinn"
    assert body["occupation_key"] == "occ_2"


def test_unknown_occupation_key_in_profile_write_returns_structured_404(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="seeker-profile-unknown-occ@example.com",
        role="job_seeker",
    )

    def raise_not_found(*_args, **_kwargs):
        raise HTTPException(status_code=404, detail="Occupation not found.")

    monkeypatch.setattr("app.modules.seeker.service.get_occupation_detail", raise_not_found)

    response = client.put(
        SEEKER_ROUTE,
        headers=auth_headers(token),
        json={
            "full_name": "Alice Example",
            "summary": "Bio",
            "location": "Tallinn",
            "occupation_key": "unknown",
        },
    )

    assert_structured_http_error(response, status_code=404, message="Occupation not found.")


def test_competency_post_creates_row_for_current_seeker(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="seeker-comp-create@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.seeker.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    response = client.post(
        SEEKER_COMPETENCIES_ROUTE,
        headers=auth_headers(token),
        json={"competency_key": "comp_1", "level": "intermediate"},
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["competency_key"] == "comp_1"
    assert body["level"] == "intermediate"


def test_duplicate_competency_post_returns_structured_409(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="seeker-comp-duplicate@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.seeker.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    first = client.post(
        SEEKER_COMPETENCIES_ROUTE,
        headers=auth_headers(token),
        json={"competency_key": "comp_1", "level": "intermediate"},
    )
    assert first.status_code == 201

    second = client.post(
        SEEKER_COMPETENCIES_ROUTE,
        headers=auth_headers(token),
        json={"competency_key": "comp_1", "level": "advanced"},
    )

    assert_structured_http_error(
        second,
        status_code=409,
        message="Competency already exists for this seeker.",
    )


def test_invalid_level_returns_422(client: TestClient):
    token = register_and_get_token(
        client,
        email="seeker-comp-invalid-level@example.com",
        role="job_seeker",
    )

    response = client.post(
        SEEKER_COMPETENCIES_ROUTE,
        headers=auth_headers(token),
        json={"competency_key": "comp_1", "level": "expert"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["details"]


def test_competency_list_returns_only_current_seeker_records(client: TestClient, monkeypatch):
    seeker_one = register_and_get_token(
        client,
        email="seeker-comp-list-1@example.com",
        role="job_seeker",
    )
    seeker_two = register_and_get_token(
        client,
        email="seeker-comp-list-2@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.seeker.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    one_create = client.post(
        SEEKER_COMPETENCIES_ROUTE,
        headers=auth_headers(seeker_one),
        json={"competency_key": "comp_1", "level": "beginner"},
    )
    assert one_create.status_code == 201

    two_create = client.post(
        SEEKER_COMPETENCIES_ROUTE,
        headers=auth_headers(seeker_two),
        json={"competency_key": "comp_2", "level": "advanced"},
    )
    assert two_create.status_code == 201

    list_response = client.get(
        SEEKER_COMPETENCIES_ROUTE,
        headers=auth_headers(seeker_one),
    )

    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["competency_key"] == "comp_1"
    assert items[0]["level"] == "beginner"


def test_competency_patch_updates_level_for_own_record(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="seeker-comp-patch-own@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.seeker.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    created = client.post(
        SEEKER_COMPETENCIES_ROUTE,
        headers=auth_headers(token),
        json={"competency_key": "comp_1", "level": "beginner"},
    )
    assert created.status_code == 201
    competency_id = created.json()["id"]

    patched = client.patch(
        f"{SEEKER_COMPETENCIES_ROUTE}/{competency_id}",
        headers=auth_headers(token),
        json={"level": "advanced"},
    )

    assert patched.status_code == 200
    assert patched.json()["level"] == "advanced"


def test_competency_patch_returns_404_for_non_owned_or_missing_record(client: TestClient, monkeypatch):
    owner_token = register_and_get_token(
        client,
        email="seeker-comp-patch-owner@example.com",
        role="job_seeker",
    )
    other_token = register_and_get_token(
        client,
        email="seeker-comp-patch-other@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.seeker.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    created = client.post(
        SEEKER_COMPETENCIES_ROUTE,
        headers=auth_headers(owner_token),
        json={"competency_key": "comp_1", "level": "intermediate"},
    )
    assert created.status_code == 201
    competency_id = created.json()["id"]

    response = client.patch(
        f"{SEEKER_COMPETENCIES_ROUTE}/{competency_id}",
        headers=auth_headers(other_token),
        json={"level": "advanced"},
    )

    assert_structured_http_error(
        response,
        status_code=404,
        message="Seeker competency not found.",
    )


def test_competency_delete_removes_own_record_and_returns_204(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="seeker-comp-delete-own@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.seeker.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    created = client.post(
        SEEKER_COMPETENCIES_ROUTE,
        headers=auth_headers(token),
        json={"competency_key": "comp_1", "level": "intermediate"},
    )
    assert created.status_code == 201
    competency_id = created.json()["id"]

    deleted = client.delete(
        f"{SEEKER_COMPETENCIES_ROUTE}/{competency_id}",
        headers=auth_headers(token),
    )
    assert deleted.status_code == 204
    assert deleted.content == b""

    listed = client.get(SEEKER_COMPETENCIES_ROUTE, headers=auth_headers(token))
    assert listed.status_code == 200
    assert listed.json() == []


def test_competency_delete_returns_404_for_non_owned_or_missing_record(client: TestClient, monkeypatch):
    owner_token = register_and_get_token(
        client,
        email="seeker-comp-delete-owner@example.com",
        role="job_seeker",
    )
    other_token = register_and_get_token(
        client,
        email="seeker-comp-delete-other@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.seeker.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    created = client.post(
        SEEKER_COMPETENCIES_ROUTE,
        headers=auth_headers(owner_token),
        json={"competency_key": "comp_1", "level": "intermediate"},
    )
    assert created.status_code == 201
    competency_id = created.json()["id"]

    response = client.delete(
        f"{SEEKER_COMPETENCIES_ROUTE}/{competency_id}",
        headers=auth_headers(other_token),
    )

    assert_structured_http_error(
        response,
        status_code=404,
        message="Seeker competency not found.",
    )
