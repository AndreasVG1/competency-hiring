from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest


API_PREFIX = "/api/v1"
REGISTER_ROUTE = f"{API_PREFIX}/auth/register"
RECRUITER_PROFILE_ROUTE = f"{API_PREFIX}/recruiter/profile"
RECRUITER_JOB_OFFERS_ROUTE = f"{API_PREFIX}/recruiter/job-offers"
RECRUITER_REQUIREMENTS_ROUTE = f"{RECRUITER_JOB_OFFERS_ROUTE}/{{job_offer_id}}/requirements"
RECRUITER_PUBLISH_ROUTE = f"{RECRUITER_JOB_OFFERS_ROUTE}/{{job_offer_id}}/publish"
RECRUITER_ARCHIVE_ROUTE = f"{RECRUITER_JOB_OFFERS_ROUTE}/{{job_offer_id}}/archive"


RECRUITER_PATHS = [
    ("GET", RECRUITER_PROFILE_ROUTE),
    ("PUT", RECRUITER_PROFILE_ROUTE),
    ("GET", RECRUITER_JOB_OFFERS_ROUTE),
    ("POST", RECRUITER_JOB_OFFERS_ROUTE),
    ("GET", f"{RECRUITER_JOB_OFFERS_ROUTE}/1"),
    ("PATCH", f"{RECRUITER_JOB_OFFERS_ROUTE}/1"),
    ("DELETE", f"{RECRUITER_JOB_OFFERS_ROUTE}/1"),
    ("POST", RECRUITER_PUBLISH_ROUTE.format(job_offer_id=1)),
    ("POST", RECRUITER_ARCHIVE_ROUTE.format(job_offer_id=1)),
    ("GET", f"{RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=1)}"),
    ("POST", f"{RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=1)}"),
    ("PATCH", f"{RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=1)}/1"),
    ("DELETE", f"{RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=1)}/1"),
]


def occupation_label_from_key(occupation_key: str) -> str:
    return occupation_key.replace("_", " ").title()


@pytest.fixture(autouse=True)
def patch_recruiter_occupation_lookup(monkeypatch):
    def fake_get_occupation_detail(*, occupation_key: str):
        if occupation_key == "unknown":
            raise HTTPException(status_code=404, detail="Occupation not found.")
        return {
            "key": occupation_key,
            "label": occupation_label_from_key(occupation_key),
            "required_competencies": [],
        }

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_occupation_detail",
        fake_get_occupation_detail,
    )


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

    if method == "PUT":
        payload = {
            "company_name": "Acme Corp",
            "contact_name": "Alice Recruiter",
        }
    elif method == "POST" and path.endswith("/requirements"):
        payload = {
            "competency_key": "comp_1",
            "priority": "must_have",
        }
    elif method == "POST" and (
        path == RECRUITER_PUBLISH_ROUTE.format(job_offer_id=1)
        or path == RECRUITER_ARCHIVE_ROUTE.format(job_offer_id=1)
    ):
        payload = None
    elif method == "POST":
        payload = {
            "occupation_key": "backend_engineer",
            "description": "Build APIs",
        }
    elif method == "PATCH" and "/requirements/" in path:
        payload = {"priority": "important"}
    elif method == "PATCH":
        payload = {"occupation_key": "updated_role", "description": "Updated Description"}
    else:
        payload = None

    return client.request(method, path, headers=headers, json=payload)


def create_offer(client: TestClient, token: str, *, occupation_key: str = "backend_engineer") -> int:
    response = client.post(
        RECRUITER_JOB_OFFERS_ROUTE,
        headers=auth_headers(token),
        json={"occupation_key": occupation_key, "description": "Build APIs"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_requirement(
    client: TestClient,
    token: str,
    *,
    job_offer_id: int,
    competency_key: str = "comp_1",
    priority: str = "must_have",
) -> int:
    response = client.post(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=job_offer_id),
        headers=auth_headers(token),
        json={"competency_key": competency_key, "priority": priority},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_recruiter_endpoints_require_authentication(client: TestClient):
    for method, path in RECRUITER_PATHS:
        response = call_endpoint(client, method, path)
        assert_structured_http_error(
            response,
            status_code=401,
            message="Could not validate credentials.",
        )


def test_seeker_token_is_forbidden_on_recruiter_endpoints(client: TestClient):
    token = register_and_get_token(
        client,
        email="seeker-recruiter-api@example.com",
        role="job_seeker",
    )

    for method, path in RECRUITER_PATHS:
        response = call_endpoint(client, method, path, token=token)
        assert_structured_http_error(
            response,
            status_code=403,
            message="You do not have permission to access this resource.",
        )


def test_profile_get_returns_404_before_creation(client: TestClient):
    token = register_and_get_token(
        client,
        email="recruiter-profile-missing@example.com",
        role="recruiter",
    )

    response = client.get(RECRUITER_PROFILE_ROUTE, headers=auth_headers(token))

    assert_structured_http_error(
        response,
        status_code=404,
        message="Recruiter profile not found.",
    )


def test_profile_put_creates_profile_when_missing(client: TestClient):
    token = register_and_get_token(
        client,
        email="recruiter-profile-create@example.com",
        role="recruiter",
    )

    response = client.put(
        RECRUITER_PROFILE_ROUTE,
        headers=auth_headers(token),
        json={"company_name": "Acme", "contact_name": "Alice"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["company_name"] == "Acme"
    assert body["contact_name"] == "Alice"


def test_profile_put_updates_existing_profile(client: TestClient):
    token = register_and_get_token(
        client,
        email="recruiter-profile-update@example.com",
        role="recruiter",
    )

    first = client.put(
        RECRUITER_PROFILE_ROUTE,
        headers=auth_headers(token),
        json={"company_name": "Acme", "contact_name": "Alice"},
    )
    assert first.status_code == 200

    second = client.put(
        RECRUITER_PROFILE_ROUTE,
        headers=auth_headers(token),
        json={"company_name": "Beta", "contact_name": "Bob"},
    )

    assert second.status_code == 200
    body = second.json()
    assert body["company_name"] == "Beta"
    assert body["contact_name"] == "Bob"


def test_job_offer_post_creates_draft_offer(client: TestClient):
    token = register_and_get_token(
        client,
        email="recruiter-offer-create@example.com",
        role="recruiter",
    )

    response = client.post(
        RECRUITER_JOB_OFFERS_ROUTE,
        headers=auth_headers(token),
        json={
            "occupation_key": "backend_engineer",
            "description": "Build APIs",
            "status": "published",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Backend Engineer"
    assert body["occupation_key"] == "backend_engineer"
    assert body["description"] == "Build APIs"
    assert body["status"] == "draft"


def test_job_offer_list_and_get_return_only_current_recruiter_records(client: TestClient):
    recruiter_one = register_and_get_token(
        client,
        email="recruiter-offer-list-1@example.com",
        role="recruiter",
    )
    recruiter_two = register_and_get_token(
        client,
        email="recruiter-offer-list-2@example.com",
        role="recruiter",
    )

    own_offer_id = create_offer(client, recruiter_one, occupation_key="offer_one")
    create_offer(client, recruiter_two, occupation_key="offer_two")

    list_response = client.get(
        RECRUITER_JOB_OFFERS_ROUTE,
        headers=auth_headers(recruiter_one),
    )

    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["id"] == own_offer_id
    assert items[0]["title"] == "Offer One"
    assert items[0]["occupation_key"] == "offer_one"

    get_response = client.get(
        f"{RECRUITER_JOB_OFFERS_ROUTE}/{own_offer_id}",
        headers=auth_headers(recruiter_one),
    )
    assert get_response.status_code == 200
    assert get_response.json()["id"] == own_offer_id


def test_job_offer_patch_updates_own_offer_fields(client: TestClient):
    token = register_and_get_token(
        client,
        email="recruiter-offer-patch-own@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, token)

    response = client.patch(
        f"{RECRUITER_JOB_OFFERS_ROUTE}/{offer_id}",
        headers=auth_headers(token),
        json={
            "occupation_key": "senior_backend_engineer",
            "description": "Build and improve APIs",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Senior Backend Engineer"
    assert body["occupation_key"] == "senior_backend_engineer"
    assert body["description"] == "Build and improve APIs"
    assert body["status"] == "draft"


def test_job_offer_get_and_patch_return_404_for_non_owned_or_missing_offer(client: TestClient):
    owner = register_and_get_token(
        client,
        email="recruiter-offer-owner@example.com",
        role="recruiter",
    )
    other = register_and_get_token(
        client,
        email="recruiter-offer-other@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, owner)

    get_response = client.get(
        f"{RECRUITER_JOB_OFFERS_ROUTE}/{offer_id}",
        headers=auth_headers(other),
    )
    assert_structured_http_error(
        get_response,
        status_code=404,
        message="Job offer not found.",
    )

    patch_response = client.patch(
        f"{RECRUITER_JOB_OFFERS_ROUTE}/{offer_id}",
        headers=auth_headers(other),
        json={"description": "Hacked"},
    )
    assert_structured_http_error(
        patch_response,
        status_code=404,
        message="Job offer not found.",
    )


def test_job_offer_publish_updates_status_to_published(client: TestClient):
    token = register_and_get_token(
        client,
        email="recruiter-offer-publish@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, token)

    response = client.post(
        RECRUITER_PUBLISH_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "published"


def test_job_offer_archive_updates_status_to_archived(client: TestClient):
    token = register_and_get_token(
        client,
        email="recruiter-offer-archive@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, token)

    published = client.post(
        RECRUITER_PUBLISH_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(token),
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    archived = client.post(
        RECRUITER_ARCHIVE_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(token),
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_job_offer_publish_and_archive_return_409_for_invalid_transitions(client: TestClient):
    token = register_and_get_token(
        client,
        email="recruiter-offer-invalid-transition@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, token)

    draft_archive = client.post(
        RECRUITER_ARCHIVE_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(token),
    )
    assert_structured_http_error(
        draft_archive,
        status_code=409,
        message="Invalid job offer status transition. draft -> archived.",
    )

    first_publish = client.post(
        RECRUITER_PUBLISH_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(token),
    )
    assert first_publish.status_code == 200
    assert first_publish.json()["status"] == "published"

    second_publish = client.post(
        RECRUITER_PUBLISH_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(token),
    )
    assert_structured_http_error(
        second_publish,
        status_code=409,
        message="Invalid job offer status transition. published -> published.",
    )


def test_job_offer_publish_and_archive_return_404_for_non_owned_or_missing_offer(client: TestClient):
    owner = register_and_get_token(
        client,
        email="recruiter-offer-transition-owner@example.com",
        role="recruiter",
    )
    other = register_and_get_token(
        client,
        email="recruiter-offer-transition-other@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, owner)

    non_owned_publish = client.post(
        RECRUITER_PUBLISH_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(other),
    )
    assert_structured_http_error(
        non_owned_publish,
        status_code=404,
        message="Job offer not found.",
    )

    missing_archive = client.post(
        RECRUITER_ARCHIVE_ROUTE.format(job_offer_id=999999),
        headers=auth_headers(owner),
    )
    assert_structured_http_error(
        missing_archive,
        status_code=404,
        message="Job offer not found.",
    )


def test_requirement_post_creates_row_for_owned_offer(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="recruiter-req-create@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, token)

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    response = client.post(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(token),
        json={"competency_key": "comp_1", "priority": "important"},
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["job_offer_id"] == offer_id
    assert body["competency_key"] == "comp_1"
    assert body["priority"] == "important"


def test_unknown_occupation_key_in_offer_write_returns_structured_404(client: TestClient):
    token = register_and_get_token(
        client,
        email="recruiter-offer-unknown-occ@example.com",
        role="recruiter",
    )

    response = client.post(
        RECRUITER_JOB_OFFERS_ROUTE,
        headers=auth_headers(token),
        json={"occupation_key": "unknown", "description": "Build APIs"},
    )

    assert_structured_http_error(response, status_code=404, message="Occupation not found.")


def test_duplicate_requirement_post_returns_structured_409(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="recruiter-req-duplicate@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, token)

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    first = client.post(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(token),
        json={"competency_key": "comp_1", "priority": "must_have"},
    )
    assert first.status_code == 201

    second = client.post(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(token),
        json={"competency_key": "comp_1", "priority": "nice_to_have"},
    )

    assert_structured_http_error(
        second,
        status_code=409,
        message="Requirement already exists for this job offer.",
    )


def test_unknown_competency_key_in_requirement_write_returns_structured_404(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="recruiter-req-unknown-key@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, token)

    def raise_not_found(*_args, **_kwargs):
        raise HTTPException(status_code=404, detail="Competency not found.")

    monkeypatch.setattr("app.modules.recruiter.service.get_competency_detail", raise_not_found)

    response = client.post(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(token),
        json={"competency_key": "unknown", "priority": "must_have"},
    )

    assert_structured_http_error(response, status_code=404, message="Competency not found.")


def test_invalid_priority_returns_422(client: TestClient):
    token = register_and_get_token(
        client,
        email="recruiter-req-invalid-priority@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, token)

    response = client.post(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(token),
        json={"competency_key": "comp_1", "priority": "critical"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["details"]


def test_requirement_list_returns_only_requirements_for_owned_offer(client: TestClient, monkeypatch):
    recruiter_one = register_and_get_token(
        client,
        email="recruiter-req-list-1@example.com",
        role="recruiter",
    )
    recruiter_two = register_and_get_token(
        client,
        email="recruiter-req-list-2@example.com",
        role="recruiter",
    )

    offer_one = create_offer(client, recruiter_one, occupation_key="offer_one")
    offer_two = create_offer(client, recruiter_two, occupation_key="offer_two")

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    create_requirement(client, recruiter_one, job_offer_id=offer_one, competency_key="comp_1", priority="must_have")
    create_requirement(client, recruiter_two, job_offer_id=offer_two, competency_key="comp_2", priority="important")

    response = client.get(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_one),
        headers=auth_headers(recruiter_one),
    )

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["job_offer_id"] == offer_one
    assert items[0]["competency_key"] == "comp_1"


def test_requirement_patch_updates_priority_for_own_requirement(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="recruiter-req-patch-own@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, token)

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    requirement_id = create_requirement(client, token, job_offer_id=offer_id)

    response = client.patch(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id) + f"/{requirement_id}",
        headers=auth_headers(token),
        json={"priority": "nice_to_have"},
    )

    assert response.status_code == 200
    assert response.json()["priority"] == "nice_to_have"


def test_requirement_patch_returns_404_for_non_owned_or_missing_requirement(client: TestClient, monkeypatch):
    owner = register_and_get_token(
        client,
        email="recruiter-req-patch-owner@example.com",
        role="recruiter",
    )
    other = register_and_get_token(
        client,
        email="recruiter-req-patch-other@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, owner)

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    requirement_id = create_requirement(client, owner, job_offer_id=offer_id)

    response = client.patch(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id) + f"/{requirement_id}",
        headers=auth_headers(other),
        json={"priority": "important"},
    )

    assert_structured_http_error(
        response,
        status_code=404,
        message="Job offer not found.",
    )


def test_requirement_delete_removes_own_requirement_and_returns_204(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="recruiter-req-delete-own@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, token)

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    requirement_id = create_requirement(client, token, job_offer_id=offer_id)

    deleted = client.delete(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id) + f"/{requirement_id}",
        headers=auth_headers(token),
    )
    assert deleted.status_code == 204
    assert deleted.content == b""

    listed = client.get(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(token),
    )
    assert listed.status_code == 200
    assert listed.json() == []


def test_requirement_delete_returns_404_for_non_owned_or_missing_requirement(client: TestClient, monkeypatch):
    owner = register_and_get_token(
        client,
        email="recruiter-req-delete-owner@example.com",
        role="recruiter",
    )
    other = register_and_get_token(
        client,
        email="recruiter-req-delete-other@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, owner)

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    requirement_id = create_requirement(client, owner, job_offer_id=offer_id)

    response = client.delete(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id) + f"/{requirement_id}",
        headers=auth_headers(other),
    )

    assert_structured_http_error(
        response,
        status_code=404,
        message="Job offer not found.",
    )


def test_job_offer_delete_removes_offer_and_requirements_and_returns_204(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="recruiter-offer-delete-own@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, token, occupation_key="backend_engineer")

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )
    requirement_id = create_requirement(client, token, job_offer_id=offer_id)
    assert requirement_id > 0

    deleted = client.delete(
        f"{RECRUITER_JOB_OFFERS_ROUTE}/{offer_id}",
        headers=auth_headers(token),
    )
    assert deleted.status_code == 204
    assert deleted.content == b""

    list_response = client.get(RECRUITER_JOB_OFFERS_ROUTE, headers=auth_headers(token))
    assert list_response.status_code == 200
    assert list_response.json() == []

    requirements_response = client.get(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(token),
    )
    assert_structured_http_error(
        requirements_response,
        status_code=404,
        message="Job offer not found.",
    )


def test_job_offer_delete_returns_404_for_non_owned_or_missing_offer(client: TestClient):
    owner = register_and_get_token(
        client,
        email="recruiter-offer-delete-owner@example.com",
        role="recruiter",
    )
    other = register_and_get_token(
        client,
        email="recruiter-offer-delete-other@example.com",
        role="recruiter",
    )
    offer_id = create_offer(client, owner, occupation_key="backend_engineer")

    non_owned = client.delete(
        f"{RECRUITER_JOB_OFFERS_ROUTE}/{offer_id}",
        headers=auth_headers(other),
    )
    assert_structured_http_error(
        non_owned,
        status_code=404,
        message="Job offer not found.",
    )

    missing = client.delete(
        f"{RECRUITER_JOB_OFFERS_ROUTE}/999999",
        headers=auth_headers(owner),
    )
    assert_structured_http_error(
        missing,
        status_code=404,
        message="Job offer not found.",
    )
