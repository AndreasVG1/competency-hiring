from fastapi import HTTPException
from fastapi.testclient import TestClient

API_PREFIX = "/api/v1"
REGISTER_ROUTE = f"{API_PREFIX}/auth/register"
SEEKER_ROUTE = f"{API_PREFIX}/seeker/profile"
SEEKER_COMPETENCIES_ROUTE = f"{API_PREFIX}/seeker/competencies"
SEEKER_JOB_OFFERS_ROUTE = f"{API_PREFIX}/seeker/job-offers"
SEEKER_APPLICATIONS_ROUTE = f"{API_PREFIX}/seeker/applications"
SEEKER_APPLY_ROUTE = f"{SEEKER_JOB_OFFERS_ROUTE}/{{job_offer_id}}/apply"
SEEKER_ANALYSIS_ROUTE = f"{SEEKER_JOB_OFFERS_ROUTE}/{{job_offer_id}}/analysis"
RECRUITER_PROFILE_ROUTE = f"{API_PREFIX}/recruiter/profile"
RECRUITER_JOB_OFFERS_ROUTE = f"{API_PREFIX}/recruiter/job-offers"
RECRUITER_REQUIREMENTS_ROUTE = f"{RECRUITER_JOB_OFFERS_ROUTE}/{{job_offer_id}}/requirements"
RECRUITER_PUBLISH_ROUTE = f"{RECRUITER_JOB_OFFERS_ROUTE}/{{job_offer_id}}/publish"

SEEKER_PATHS = [
    ("GET", SEEKER_ROUTE),
    ("PUT", SEEKER_ROUTE),
    ("DELETE", SEEKER_ROUTE),
    ("GET", SEEKER_COMPETENCIES_ROUTE),
    ("POST", SEEKER_COMPETENCIES_ROUTE),
    ("PATCH", f"{SEEKER_COMPETENCIES_ROUTE}/1"),
    ("DELETE", f"{SEEKER_COMPETENCIES_ROUTE}/1"),
    ("GET", SEEKER_JOB_OFFERS_ROUTE),
    ("GET", f"{SEEKER_JOB_OFFERS_ROUTE}/1"),
    ("GET", SEEKER_ANALYSIS_ROUTE.format(job_offer_id=1)),
    ("POST", SEEKER_APPLY_ROUTE.format(job_offer_id=1)),
    ("GET", SEEKER_APPLICATIONS_ROUTE),
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


def create_recruiter_offer(client: TestClient, token: str, *, occupation_key: str, description: str) -> int:
    response = client.post(
        RECRUITER_JOB_OFFERS_ROUTE,
        headers=auth_headers(token),
        json={"occupation_key": occupation_key, "description": description},
    )
    assert response.status_code == 201
    return response.json()["id"]


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
    json = None if path.endswith("/apply") else json_by_method.get(method)
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


def test_profile_delete_removes_profile_and_competencies_and_returns_204(client: TestClient, monkeypatch):
    token = register_and_get_token(
        client,
        email="seeker-profile-delete-own@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.seeker.service.get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": "Occupation"},
    )
    monkeypatch.setattr(
        "app.modules.seeker.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency", "code": "C", "ekr_level": 4},
    )

    created_profile = client.put(
        SEEKER_ROUTE,
        headers=auth_headers(token),
        json={
            "full_name": "Alice Example",
            "summary": "Bio",
            "location": "Tallinn",
            "occupation_key": "occ_1",
        },
    )
    assert created_profile.status_code == 200

    created_competency = client.post(
        SEEKER_COMPETENCIES_ROUTE,
        headers=auth_headers(token),
        json={"competency_key": "comp_1", "level": "intermediate"},
    )
    assert created_competency.status_code == 201

    deleted = client.delete(SEEKER_ROUTE, headers=auth_headers(token))
    assert deleted.status_code == 204
    assert deleted.content == b""

    profile_after_delete = client.get(SEEKER_ROUTE, headers=auth_headers(token))
    assert_structured_http_error(
        profile_after_delete,
        status_code=404,
        message="Seeker profile not found.",
    )

    competencies_after_delete = client.get(SEEKER_COMPETENCIES_ROUTE, headers=auth_headers(token))
    assert competencies_after_delete.status_code == 200
    assert competencies_after_delete.json() == []


def test_profile_delete_returns_404_when_profile_is_missing(client: TestClient):
    token = register_and_get_token(
        client,
        email="seeker-profile-delete-missing@example.com",
        role="job_seeker",
    )

    response = client.delete(SEEKER_ROUTE, headers=auth_headers(token))
    assert_structured_http_error(
        response,
        status_code=404,
        message="Seeker profile not found.",
    )


def test_job_offer_marketplace_list_returns_only_published_with_filters_and_pagination(client: TestClient, monkeypatch):
    recruiter_token = register_and_get_token(
        client,
        email="recruiter-marketplace-list@example.com",
        role="recruiter",
    )
    seeker_token = register_and_get_token(
        client,
        email="seeker-marketplace-list@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": occupation_key.replace("_", " ").title()},
    )

    recruiter_profile = client.put(
        RECRUITER_PROFILE_ROUTE,
        headers=auth_headers(recruiter_token),
        json={"company_name": "Acme", "contact_name": "Alice Recruiter"},
    )
    assert recruiter_profile.status_code == 200

    backend_offer_id = create_recruiter_offer(
        client,
        recruiter_token,
        occupation_key="backend_engineer",
        description="Build Python APIs for the platform",
    )
    frontend_offer_id = create_recruiter_offer(
        client,
        recruiter_token,
        occupation_key="frontend_engineer",
        description="Build Vue interfaces",
    )
    draft_offer_id = create_recruiter_offer(
        client,
        recruiter_token,
        occupation_key="data_analyst",
        description="Analyze marketplace trends",
    )
    assert draft_offer_id > 0

    publish_one = client.post(
        RECRUITER_PUBLISH_ROUTE.format(job_offer_id=backend_offer_id),
        headers=auth_headers(recruiter_token),
    )
    publish_two = client.post(
        RECRUITER_PUBLISH_ROUTE.format(job_offer_id=frontend_offer_id),
        headers=auth_headers(recruiter_token),
    )
    assert publish_one.status_code == 200
    assert publish_two.status_code == 200

    listed = client.get(SEEKER_JOB_OFFERS_ROUTE, headers=auth_headers(seeker_token))
    assert listed.status_code == 200
    items = listed.json()
    listed_ids = {item["id"] for item in items}
    assert listed_ids == {backend_offer_id, frontend_offer_id}
    assert all(item["company_name"] == "Acme" for item in items)
    assert all(item["published_at"] for item in items)

    filtered_by_query = client.get(
        SEEKER_JOB_OFFERS_ROUTE,
        headers=auth_headers(seeker_token),
        params={"query": "python"},
    )
    assert filtered_by_query.status_code == 200
    query_items = filtered_by_query.json()
    assert len(query_items) == 1
    assert query_items[0]["id"] == backend_offer_id

    filtered_by_occupation = client.get(
        SEEKER_JOB_OFFERS_ROUTE,
        headers=auth_headers(seeker_token),
        params={"occupation_key": "frontend_engineer"},
    )
    assert filtered_by_occupation.status_code == 200
    occupation_items = filtered_by_occupation.json()
    assert len(occupation_items) == 1
    assert occupation_items[0]["id"] == frontend_offer_id

    paged = client.get(
        SEEKER_JOB_OFFERS_ROUTE,
        headers=auth_headers(seeker_token),
        params={"limit": 1, "offset": 1},
    )
    assert paged.status_code == 200
    assert len(paged.json()) == 1


def test_job_offer_marketplace_detail_returns_published_offer_with_requirements(client: TestClient, monkeypatch):
    recruiter_token = register_and_get_token(
        client,
        email="recruiter-marketplace-detail@example.com",
        role="recruiter",
    )
    seeker_token = register_and_get_token(
        client,
        email="seeker-marketplace-detail@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": occupation_key.replace("_", " ").title()},
    )
    monkeypatch.setattr(
        "app.modules.recruiter.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": competency_key.replace("_", " ").title()},
    )

    recruiter_profile = client.put(
        RECRUITER_PROFILE_ROUTE,
        headers=auth_headers(recruiter_token),
        json={"company_name": "Acme", "contact_name": "Alice Recruiter"},
    )
    assert recruiter_profile.status_code == 200

    offer_id = create_recruiter_offer(
        client,
        recruiter_token,
        occupation_key="backend_engineer",
        description="Build APIs",
    )

    requirement = client.post(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(recruiter_token),
        json={"competency_key": "python", "priority": "must_have"},
    )
    assert requirement.status_code == 201

    published = client.post(
        RECRUITER_PUBLISH_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(recruiter_token),
    )
    assert published.status_code == 200

    response = client.get(
        f"{SEEKER_JOB_OFFERS_ROUTE}/{offer_id}",
        headers=auth_headers(seeker_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == offer_id
    assert body["company_name"] == "Acme"
    assert body["description"] == "Build APIs"
    assert body["requirements"] == [{"competency_key": "python", "priority": "must_have"}]


def test_job_offer_marketplace_detail_returns_404_for_draft_or_missing_offer(client: TestClient, monkeypatch):
    recruiter_token = register_and_get_token(
        client,
        email="recruiter-marketplace-detail-404@example.com",
        role="recruiter",
    )
    seeker_token = register_and_get_token(
        client,
        email="seeker-marketplace-detail-404@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": occupation_key.replace("_", " ").title()},
    )

    draft_offer_id = create_recruiter_offer(
        client,
        recruiter_token,
        occupation_key="backend_engineer",
        description="Draft only",
    )

    draft_response = client.get(
        f"{SEEKER_JOB_OFFERS_ROUTE}/{draft_offer_id}",
        headers=auth_headers(seeker_token),
    )
    assert_structured_http_error(
        draft_response,
        status_code=404,
        message="Published job offer not found.",
    )

    missing_response = client.get(
        f"{SEEKER_JOB_OFFERS_ROUTE}/999999",
        headers=auth_headers(seeker_token),
    )
    assert_structured_http_error(
        missing_response,
        status_code=404,
        message="Published job offer not found.",
    )


def test_private_job_offer_analysis_returns_current_seekers_result(client: TestClient, monkeypatch):
    recruiter_token = register_and_get_token(
        client,
        email="recruiter-analysis-happy@example.com",
        role="recruiter",
    )
    seeker_one_token = register_and_get_token(
        client,
        email="seeker-analysis-happy-one@example.com",
        role="job_seeker",
    )
    seeker_two_token = register_and_get_token(
        client,
        email="seeker-analysis-happy-two@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": occupation_key.replace("_", " ").title()},
    )
    monkeypatch.setattr(
        "app.modules.recruiter.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": competency_key},
    )
    monkeypatch.setattr(
        "app.modules.seeker.service.get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": competency_key, "code": "C", "ekr_level": 4},
    )

    offer_id = create_recruiter_offer(
        client,
        recruiter_token,
        occupation_key="backend_engineer",
        description="Build APIs",
    )

    requirement_one = client.post(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(recruiter_token),
        json={"competency_key": "comp_api", "priority": "must_have"},
    )
    assert requirement_one.status_code == 201
    requirement_two = client.post(
        RECRUITER_REQUIREMENTS_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(recruiter_token),
        json={"competency_key": "comp_sql", "priority": "important"},
    )
    assert requirement_two.status_code == 201

    publish = client.post(
        RECRUITER_PUBLISH_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(recruiter_token),
    )
    assert publish.status_code == 200

    seeker_one_comp = client.post(
        SEEKER_COMPETENCIES_ROUTE,
        headers=auth_headers(seeker_one_token),
        json={"competency_key": "comp_api", "level": "intermediate"},
    )
    assert seeker_one_comp.status_code == 201

    seeker_one_analysis = client.get(
        SEEKER_ANALYSIS_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(seeker_one_token),
    )
    assert seeker_one_analysis.status_code == 200
    seeker_one_body = seeker_one_analysis.json()
    assert seeker_one_body["scope"] == "private_preview"
    assert seeker_one_body["algorithm_version"] == "v2_exact_priority_level_dual_signal"
    assert seeker_one_body["job_offer_id"] == offer_id
    assert seeker_one_body["status"] == "ok"
    assert seeker_one_body["score"] == 62.5
    assert seeker_one_body["totals"]["matched_count"] == 1
    assert seeker_one_body["totals"]["missing_count"] == 1

    seeker_two_analysis = client.get(
        SEEKER_ANALYSIS_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(seeker_two_token),
    )
    assert seeker_two_analysis.status_code == 200
    seeker_two_body = seeker_two_analysis.json()
    assert seeker_two_body["scope"] == "private_preview"
    assert seeker_two_body["algorithm_version"] == "v2_exact_priority_level_dual_signal"
    assert seeker_two_body["job_offer_id"] == offer_id
    assert seeker_two_body["status"] == "ok_with_must_have_gaps"
    assert seeker_two_body["score"] == 0.0
    assert seeker_two_body["critical_gap_present"] is True
    assert seeker_two_body["totals"]["matched_count"] == 0
    assert seeker_two_body["totals"]["missing_count"] == 2

    assert seeker_one_body["seeker_user_id"] != seeker_two_body["seeker_user_id"]


def test_private_job_offer_analysis_returns_404_for_draft_or_missing_offer(client: TestClient, monkeypatch):
    recruiter_token = register_and_get_token(
        client,
        email="recruiter-analysis-404@example.com",
        role="recruiter",
    )
    seeker_token = register_and_get_token(
        client,
        email="seeker-analysis-404@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": occupation_key.replace("_", " ").title()},
    )

    draft_offer_id = create_recruiter_offer(
        client,
        recruiter_token,
        occupation_key="backend_engineer",
        description="Draft only",
    )

    draft_response = client.get(
        SEEKER_ANALYSIS_ROUTE.format(job_offer_id=draft_offer_id),
        headers=auth_headers(seeker_token),
    )
    assert_structured_http_error(
        draft_response,
        status_code=404,
        message="Published job offer not found.",
    )

    missing_response = client.get(
        SEEKER_ANALYSIS_ROUTE.format(job_offer_id=999999),
        headers=auth_headers(seeker_token),
    )
    assert_structured_http_error(
        missing_response,
        status_code=404,
        message="Published job offer not found.",
    )


def test_apply_to_published_job_offer_creates_application(client: TestClient, monkeypatch):
    recruiter_token = register_and_get_token(
        client,
        email="recruiter-apply-create@example.com",
        role="recruiter",
    )
    seeker_token = register_and_get_token(
        client,
        email="seeker-apply-create@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": occupation_key.replace("_", " ").title()},
    )

    profile_response = client.put(
        SEEKER_ROUTE,
        headers=auth_headers(seeker_token),
        json={
            "full_name": "Alice Example",
            "summary": "Ready to apply",
            "location": "Tallinn",
            "occupation_key": None,
        },
    )
    assert profile_response.status_code == 200

    offer_id = create_recruiter_offer(
        client,
        recruiter_token,
        occupation_key="backend_engineer",
        description="Build APIs",
    )
    publish = client.post(
        RECRUITER_PUBLISH_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(recruiter_token),
    )
    assert publish.status_code == 200

    response = client.post(
        SEEKER_APPLY_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(seeker_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["job_offer_id"] == offer_id
    assert body["consent_given_at"]
    assert body["created_at"]


def test_apply_duplicate_returns_structured_409(client: TestClient, monkeypatch):
    recruiter_token = register_and_get_token(
        client,
        email="recruiter-apply-duplicate@example.com",
        role="recruiter",
    )
    seeker_token = register_and_get_token(
        client,
        email="seeker-apply-duplicate@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": occupation_key.replace("_", " ").title()},
    )

    profile_response = client.put(
        SEEKER_ROUTE,
        headers=auth_headers(seeker_token),
        json={
            "full_name": "Alice Example",
            "summary": "Ready to apply",
            "location": "Tallinn",
            "occupation_key": None,
        },
    )
    assert profile_response.status_code == 200

    offer_id = create_recruiter_offer(
        client,
        recruiter_token,
        occupation_key="backend_engineer",
        description="Build APIs",
    )
    publish = client.post(
        RECRUITER_PUBLISH_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(recruiter_token),
    )
    assert publish.status_code == 200

    first = client.post(
        SEEKER_APPLY_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(seeker_token),
    )
    assert first.status_code == 201

    second = client.post(
        SEEKER_APPLY_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(seeker_token),
    )
    assert_structured_http_error(
        second,
        status_code=409,
        message="Application already exists for this seeker and job offer.",
    )


def test_list_my_applications_returns_only_current_seekers_rows(client: TestClient, monkeypatch):
    recruiter_token = register_and_get_token(
        client,
        email="recruiter-seeker-app-list@example.com",
        role="recruiter",
    )
    seeker_one_token = register_and_get_token(
        client,
        email="seeker-app-list-1@example.com",
        role="job_seeker",
    )
    seeker_two_token = register_and_get_token(
        client,
        email="seeker-app-list-2@example.com",
        role="job_seeker",
    )

    monkeypatch.setattr(
        "app.modules.recruiter.service.get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": occupation_key.replace("_", " ").title()},
    )

    for token, name in ((seeker_one_token, "Seeker One"), (seeker_two_token, "Seeker Two")):
        profile_response = client.put(
            SEEKER_ROUTE,
            headers=auth_headers(token),
            json={
                "full_name": name,
                "summary": "Ready to apply",
                "location": "Tallinn",
                "occupation_key": None,
            },
        )
        assert profile_response.status_code == 200

    offer_id = create_recruiter_offer(
        client,
        recruiter_token,
        occupation_key="backend_engineer",
        description="Build APIs",
    )
    publish = client.post(
        RECRUITER_PUBLISH_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(recruiter_token),
    )
    assert publish.status_code == 200

    apply_one = client.post(
        SEEKER_APPLY_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(seeker_one_token),
    )
    assert apply_one.status_code == 201

    apply_two = client.post(
        SEEKER_APPLY_ROUTE.format(job_offer_id=offer_id),
        headers=auth_headers(seeker_two_token),
    )
    assert apply_two.status_code == 201

    listed_one = client.get(
        SEEKER_APPLICATIONS_ROUTE,
        headers=auth_headers(seeker_one_token),
    )
    assert listed_one.status_code == 200
    items_one = listed_one.json()
    assert len(items_one) == 1
    assert items_one[0]["job_offer_id"] == offer_id

    listed_two = client.get(
        SEEKER_APPLICATIONS_ROUTE,
        headers=auth_headers(seeker_two_token),
    )
    assert listed_two.status_code == 200
    items_two = listed_two.json()
    assert len(items_two) == 1
    assert items_two[0]["job_offer_id"] == offer_id
    assert items_one[0]["id"] != items_two[0]["id"]
