from importlib import import_module
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

API_PREFIX = "/api/v1"
REGISTER_ROUTE = f"{API_PREFIX}/auth/register"
OCCUPATIONS_ROUTE = f"{API_PREFIX}/catalog/occupations"
COMPETENCIES_ROUTE = f"{API_PREFIX}/catalog/competencies"

def import_or_xfail(module_name: str):
    try:
        return import_module(module_name)
    except ModuleNotFoundError:
        pytest.xfail(f"{module_name} is not implemented yet.")


def get_catalog_modules_or_xfail():
    router_module = import_or_xfail("app.modules.catalog.router")
    service_module = import_or_xfail("app.modules.catalog.service")
    return router_module, service_module


def patch_callable(monkeypatch, router_module: Any, service_module: Any, candidates: list[str], stub) -> None:
    patched = False

    for module in (router_module, service_module):
        for name in candidates:
            if hasattr(module, name) and callable(getattr(module, name)):
                monkeypatch.setattr(module, name, stub)
                patched = True

    if not patched:
        pytest.xfail(f"Could not patch any callable. Expected one of: {candidates}")


def register_and_get_token(client: TestClient, *, role: str = "job_seeker") -> str:
    response = client.post(
        REGISTER_ROUTE,
        json={
            "email": f"catalog-{role}@example.com",
            "password": "StrongPassword123!",
            "role": role,
        },
    )
    assert response.status_code in (200, 201)
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def assert_structured_http_error(response, *, status_code: int) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert body["error"] == "http_error"
    assert body["details"]
    assert "message" in body["details"][0]


def assert_absent_forbidden_id_fields(payload: Any) -> None:
    forbidden = {"id", "neo4j_id", "element_id", "node_id", "internal_id"}

    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key not in forbidden
            assert_absent_forbidden_id_fields(value)
    elif isinstance(payload, list):
        for value in payload:
            assert_absent_forbidden_id_fields(value)


@pytest.mark.parametrize(
    "path",
    [
        f"{COMPETENCIES_ROUTE}?query=med",
        f"{COMPETENCIES_ROUTE}/comp_1",
        f"{OCCUPATIONS_ROUTE}?query=ster",
        f"{OCCUPATIONS_ROUTE}/occ_1",
    ],
)
def test_catalog_endpoints_require_authentication(client: TestClient, path: str):
    get_catalog_modules_or_xfail()

    response = client.get(path)
    if response.status_code == 404:
        pytest.xfail("Catalog routes are not wired into the API router yet.")

    assert_structured_http_error(response, status_code=401)


def test_competency_search_returns_deterministic_contract_shape(client: TestClient, monkeypatch):
    router_module, service_module = get_catalog_modules_or_xfail()
    token = register_and_get_token(client)

    def fake_search_competencies(*_args, **_kwargs):
        return [
            {
                "key": "comp_1",
                "label": "Alpha Competency",
                "code": "COMP-001",
                "ekr_level": 4,
                "id": "neo4j-internal-should-not-leak",
            },
            {
                "key": "comp_2",
                "label": "Beta Competency",
                "code": "COMP-002",
                "ekr_level": 3,
                "node_id": 123,
            },
        ]

    patch_callable(
        monkeypatch,
        router_module,
        service_module,
        ["search_competencies", "list_competencies", "get_competencies"],
        fake_search_competencies,
    )

    response = client.get(
        COMPETENCIES_ROUTE,
        params={"query": "comp", "limit": 2},
        headers=auth_headers(token),
    )

    if response.status_code == 404:
        pytest.xfail("Catalog routes are not wired into the API router yet.")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert [item["key"] for item in body] == ["comp_1", "comp_2"]
    assert [item["label"] for item in body] == ["Alpha Competency", "Beta Competency"]

    for item in body:
        assert {"key", "label"}.issubset(item.keys())
        assert "id" not in item
        assert "node_id" not in item
        assert "internal_id" not in item


def test_unknown_catalog_keys_return_structured_404(client: TestClient, monkeypatch):
    router_module, service_module = get_catalog_modules_or_xfail()
    token = register_and_get_token(client)

    def fake_competency_detail(*_args, **_kwargs):
        raise HTTPException(status_code=404, detail="Competency not found.")

    def fake_occupation_detail(*_args, **_kwargs):
        raise HTTPException(status_code=404, detail="Occupation not found.")

    patch_callable(
        monkeypatch,
        router_module,
        service_module,
        ["get_competency_detail", "get_competency", "read_competency_detail"],
        fake_competency_detail,
    )
    patch_callable(
        monkeypatch,
        router_module,
        service_module,
        ["get_occupation_detail", "get_occupation", "read_occupation_detail"],
        fake_occupation_detail,
    )

    competency_response = client.get(
        f"{COMPETENCIES_ROUTE}/unknown_key",
        headers=auth_headers(token),
    )
    occupation_response = client.get(
        f"{OCCUPATIONS_ROUTE}/unknown_key",
        headers=auth_headers(token),
    )

    if competency_response.status_code == 404 and occupation_response.status_code == 404:
        competency_body = competency_response.json()
        if isinstance(competency_body, dict) and "error" not in competency_body:
            pytest.xfail("Catalog routes are not wired into the API router yet.")

    assert_structured_http_error(competency_response, status_code=404)
    assert_structured_http_error(occupation_response, status_code=404)


def test_competency_detail_includes_activity_indicators(client: TestClient, monkeypatch):
    router_module, service_module = get_catalog_modules_or_xfail()
    token = register_and_get_token(client)

    def fake_competency_detail(*_args, **_kwargs):
        return {
            "key": "comp_1",
            "label": "Sterilization Basics",
            "code": "COMP-001",
            "ekr_level": 4,
            "activity_indicators": [
                {
                    "key": "ai_1",
                    "text": "Follows sterilization workflow exactly.",
                    "code": "AI-001",
                },
                {
                    "key": "ai_2",
                    "text": "Logs post-cleaning checks.",
                    "code": "AI-002",
                },
            ],
        }

    patch_callable(
        monkeypatch,
        router_module,
        service_module,
        ["get_competency_detail", "get_competency", "read_competency_detail"],
        fake_competency_detail,
    )

    response = client.get(
        f"{COMPETENCIES_ROUTE}/comp_1",
        headers=auth_headers(token),
    )

    if response.status_code == 404:
        pytest.xfail("Catalog routes are not wired into the API router yet.")

    assert response.status_code == 200
    body = response.json()
    assert body["key"] == "comp_1"
    assert body["label"] == "Sterilization Basics"
    assert [item["key"] for item in body["activity_indicators"]] == ["ai_1", "ai_2"]
    assert [item["text"] for item in body["activity_indicators"]] == [
        "Follows sterilization workflow exactly.",
        "Logs post-cleaning checks.",
    ]


def test_catalog_search_returns_empty_list_for_no_matches(client: TestClient, monkeypatch):
    router_module, service_module = get_catalog_modules_or_xfail()
    token = register_and_get_token(client)

    patch_callable(
        monkeypatch,
        router_module,
        service_module,
        ["search_competencies", "list_competencies", "get_competencies"],
        lambda *_args, **_kwargs: [],
    )
    patch_callable(
        monkeypatch,
        router_module,
        service_module,
        ["search_occupations", "list_occupations", "get_occupations"],
        lambda *_args, **_kwargs: [],
    )

    competencies_response = client.get(
        COMPETENCIES_ROUTE,
        params={"query": "nope", "limit": 10},
        headers=auth_headers(token),
    )
    occupations_response = client.get(
        OCCUPATIONS_ROUTE,
        params={"query": "nope", "limit": 10},
        headers=auth_headers(token),
    )

    if competencies_response.status_code == 404 and occupations_response.status_code == 404:
        pytest.xfail("Catalog routes are not wired into the API router yet.")

    assert competencies_response.status_code == 200
    assert occupations_response.status_code == 200
    assert competencies_response.json() == []
    assert occupations_response.json() == []


def test_catalog_payload_never_exposes_neo4j_internal_id_fields(client: TestClient, monkeypatch):
    router_module, service_module = get_catalog_modules_or_xfail()
    token = register_and_get_token(client)

    def fake_competency_detail(*_args, **_kwargs):
        return {
            "key": "comp_1",
            "label": "Sterilization Basics",
            "code": "COMP-001",
            "ekr_level": 4,
            "activity_indicators": [
                {
                    "key": "ai_1",
                    "text": "Handles sterilization procedures.",
                    "code": "AI-001",
                    "neo4j_id": 888,
                }
            ],
            "id": "internal-node-id",
            "neo4j_id": 101,
        }

    def fake_occupation_detail(*_args, **_kwargs):
        return {
            "key": "occ_1",
            "label": "Sterilization Technician",
            "id": "occ-internal",
            "required_competencies": [
                {
                    "key": "comp_1",
                    "label": "Sterilization Basics",
                    "element_id": "internal-edge-id",
                }
            ],
        }

    patch_callable(
        monkeypatch,
        router_module,
        service_module,
        ["get_competency_detail", "get_competency", "read_competency_detail"],
        fake_competency_detail,
    )
    patch_callable(
        monkeypatch,
        router_module,
        service_module,
        ["get_occupation_detail", "get_occupation", "read_occupation_detail"],
        fake_occupation_detail,
    )

    competency_response = client.get(
        f"{COMPETENCIES_ROUTE}/comp_1",
        headers=auth_headers(token),
    )
    occupation_response = client.get(
        f"{OCCUPATIONS_ROUTE}/occ_1",
        headers=auth_headers(token),
    )

    if competency_response.status_code == 404 and occupation_response.status_code == 404:
        pytest.xfail("Catalog routes are not wired into the API router yet.")

    assert competency_response.status_code == 200
    assert occupation_response.status_code == 200

    assert_absent_forbidden_id_fields(competency_response.json())
    assert_absent_forbidden_id_fields(occupation_response.json())
