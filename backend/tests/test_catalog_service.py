from importlib import import_module
import inspect
from typing import Any

import pytest


class FakeRecord(dict):
    def data(self) -> dict[str, Any]:
        return dict(self)


class FakeResult:
    def __init__(self, records: list[dict[str, Any]]):
        self._records = [FakeRecord(record) for record in records]

    def data(self) -> list[dict[str, Any]]:
        return [record.data() for record in self._records]

    def single(self):
        return self._records[0] if self._records else None

    def __iter__(self):
        return iter(self._records)


class FakeTx:
    def __init__(self, records_provider):
        self._records_provider = records_provider

    def run(self, *args, **kwargs):
        return FakeResult(self._records_provider(*args, **kwargs))


class FakeSession:
    def __init__(self, records_provider):
        self._records_provider = records_provider

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False

    def run(self, *args, **kwargs):
        return FakeResult(self._records_provider(*args, **kwargs))

    def execute_read(self, fn, *args, **kwargs):
        tx = FakeTx(self._records_provider)
        return fn(tx, *args, **kwargs)


class FakeDriver:
    def __init__(self, records_provider):
        self._records_provider = records_provider

    def session(self, *args, **kwargs):
        del args, kwargs
        return FakeSession(self._records_provider)


def import_or_xfail(module_name: str):
    try:
        return import_module(module_name)
    except ModuleNotFoundError:
        pytest.xfail(f"{module_name} is not implemented yet.")


def resolve_callable(module: Any, candidates: list[str], *, purpose: str) -> Any:
    for name in candidates:
        candidate = getattr(module, name, None)
        if callable(candidate):
            return candidate
    pytest.xfail(f"Could not resolve callable for {purpose}. Expected one of: {candidates}")


def invoke_with_supported_signature(func: Any, **kwargs: Any) -> Any:
    signature = inspect.signature(func)
    accepted: dict[str, Any] = {}

    for name in signature.parameters:
        if name in kwargs:
            accepted[name] = kwargs[name]

    return func(**accepted)


def install_fake_driver(monkeypatch, fake_driver: FakeDriver) -> None:
    for module_name in ["app.modules.catalog.service", "app.modules.catalog.repository"]:
        try:
            module = import_module(module_name)
        except ModuleNotFoundError:
            continue

        if hasattr(module, "get_neo4j_driver"):
            monkeypatch.setattr(module, "get_neo4j_driver", lambda *_args, **_kwargs: fake_driver)


def catalog_records_provider(*args, **kwargs) -> list[dict[str, Any]]:
    params: dict[str, Any] = {}

    if len(args) >= 2 and isinstance(args[1], dict):
        params.update(args[1])
    params.update(kwargs)

    query = str(args[0]) if args else ""

    if "competency_key" in params:
        if params["competency_key"] == "unknown":
            return []
        return [
            {
                "id": params["competency_key"],
                "name": "Meditsiiniseadmete hooldamine",
                "key": params["competency_key"],
                "label": "Meditsiiniseadmete hooldamine",
                "code": "COMP-UNIQUE-001",
                "ekr_level": 4,
                "competency": {
                    "id": params["competency_key"],
                    "name": "Meditsiiniseadmete hooldamine",
                    "code": "COMP-UNIQUE-001",
                    "ekr_level": 4,
                },
                "activity_indicators": [
                    {
                        "id": "ai_2",
                        "text": "Kontrollib dokumenteerimise täpsust.",
                        "code": "AI-002",
                    },
                    {
                        "id": "ai_1",
                        "text": "Hooldab seadmeid vastavalt juhendile.",
                        "code": "AI-001",
                    },
                ],
            }
        ]

    if "occupation_key" in params:
        if params["occupation_key"] == "unknown":
            return []
        return [
            {
                "id": params["occupation_key"],
                "name": "Sterilisatsioonitehnik",
                "key": params["occupation_key"],
                "label": "Sterilisatsioonitehnik",
                "required_competencies": [
                    {
                        "id": "comp_1",
                        "name": "Meditsiiniseadmete hooldamine",
                        "key": "comp_1",
                        "label": "Meditsiiniseadmete hooldamine",
                    }
                ],
            }
        ]

    if "Occupation" in query or "occupation" in query:
        rows = [
            {
                "id": "occ_2",
                "name": "Anestesioloogiatehnik",
                "key": "occ_2",
                "label": "Anestesioloogiatehnik",
            },
            {
                "id": "occ_1",
                "name": "Sterilisatsioonitehnik",
                "key": "occ_1",
                "label": "Sterilisatsioonitehnik",
            },
        ]
        rows.sort(key=lambda item: (item["name"], item["id"]))

        limit = params.get("limit")
        if isinstance(limit, int):
            return rows[:limit]
        return rows

    rows = [
        {
            "id": "comp_2",
            "name": "Varustuse dokumenteerimine",
            "key": "comp_2",
            "label": "Varustuse dokumenteerimine",
            "code": "COMP-UNIQUE-002",
            "ekr_level": 3,
        },
        {
            "id": "comp_1",
            "name": "Meditsiiniseadmete hooldamine",
            "key": "comp_1",
            "label": "Meditsiiniseadmete hooldamine",
            "code": "COMP-UNIQUE-001",
            "ekr_level": 4,
        },
        {
            "id": "comp_3",
            "name": "Aseptika põhialused",
            "key": "comp_3",
            "label": "Aseptika põhialused",
            "code": "COMP-UNIQUE-003",
            "ekr_level": 2,
        },
    ]
    rows.sort(key=lambda item: (item["name"], item["id"]))

    limit = params.get("limit")
    if isinstance(limit, int):
        return rows[:limit]
    return rows


def test_service_maps_graph_fields_to_api_fields(monkeypatch):
    service_module = import_or_xfail("app.modules.catalog.service")
    install_fake_driver(monkeypatch, FakeDriver(catalog_records_provider))

    search_competencies = resolve_callable(
        service_module,
        ["search_competencies", "list_competencies", "get_competencies"],
        purpose="competency search",
    )
    search_occupations = resolve_callable(
        service_module,
        ["search_occupations", "list_occupations", "get_occupations"],
        purpose="occupation search",
    )

    competencies = invoke_with_supported_signature(
        search_competencies,
        query="comp",
        limit=2,
    )
    occupations = invoke_with_supported_signature(
        search_occupations,
        query="tech",
        limit=2,
    )

    assert competencies
    assert occupations
    assert isinstance(competencies, list)
    assert isinstance(occupations, list)

    for item in competencies:
        assert "key" in item
        assert "label" in item
        assert "id" not in item
        assert "name" not in item

    for item in occupations:
        assert "key" in item
        assert "label" in item
        assert "id" not in item
        assert "name" not in item


def test_service_returns_required_competencies_in_occupation_detail(monkeypatch):
    service_module = import_or_xfail("app.modules.catalog.service")
    install_fake_driver(monkeypatch, FakeDriver(catalog_records_provider))

    get_occupation_detail = resolve_callable(
        service_module,
        ["get_occupation_detail", "get_occupation", "read_occupation_detail"],
        purpose="occupation detail",
    )

    detail = invoke_with_supported_signature(
        get_occupation_detail,
        occupation_key="occ_1",
    )

    assert detail
    assert isinstance(detail, dict)
    assert detail["key"] == "occ_1"
    assert "required_competencies" in detail
    assert isinstance(detail["required_competencies"], list)
    assert detail["required_competencies"]
    assert {"key", "label"}.issubset(detail["required_competencies"][0].keys())


def test_service_ordering_limit_and_unique_code_assumptions(monkeypatch):
    service_module = import_or_xfail("app.modules.catalog.service")
    install_fake_driver(monkeypatch, FakeDriver(catalog_records_provider))

    search_competencies = resolve_callable(
        service_module,
        ["search_competencies", "list_competencies", "get_competencies"],
        purpose="competency search",
    )
    get_competency_detail = resolve_callable(
        service_module,
        ["get_competency_detail", "get_competency", "read_competency_detail"],
        purpose="competency detail",
    )

    limited_results = invoke_with_supported_signature(
        search_competencies,
        query="comp",
        limit=2,
    )

    assert isinstance(limited_results, list)
    assert len(limited_results) <= 2

    labels = [item["label"] for item in limited_results]
    assert labels == sorted(labels) or len(labels) <= 1

    detail = invoke_with_supported_signature(
        get_competency_detail,
        competency_key="comp_1",
    )
    assert detail["key"] == "comp_1"
    assert detail["code"] == "COMP-UNIQUE-001"
    assert detail["activity_indicators"] == [
        {
            "key": "ai_2",
            "text": "Kontrollib dokumenteerimise täpsust.",
            "code": "AI-002",
        },
        {
            "key": "ai_1",
            "text": "Hooldab seadmeid vastavalt juhendile.",
            "code": "AI-001",
        },
    ]
