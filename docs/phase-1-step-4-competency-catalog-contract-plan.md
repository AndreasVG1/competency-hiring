# Phase 1 Step 4 Detailed Plan: Competency Catalog Contract

## Summary

This document expands step 4 from `docs/phase-1-profile-setup-plan.md` into an implementation-ready plan for the backend competency catalog contract.

Goal for this step:

- expose Neo4j-backed read-only catalog endpoints through FastAPI
- keep frontend access strictly via backend APIs (no direct Neo4j access)
- provide stable keys for SQLite references (`occupation_key`, `competency_key`)
- keep route handlers thin and place catalog rules in service-level code

This design follows the constraints in `AGENTS.md`:

- modular monolith (no service split)
- clear business logic boundaries
- SQLite for business data, Neo4j for competency graph read models
- transparent deterministic behavior (no hidden inference/ranking)
- privacy-aware backend control (server-side access checks)

## Current Context and Input Graph

You provided the current graph model and example data:

- `:Occupation {id, name}`
- `:Competency {id, name, ekr_level, code}`
- `:ActivityIndicator {id, text, code}`
- `:CompetencyElement {id, text, type}`
- relations:
  - `(Occupation)-[:REQUIRES_COMPETENCY]->(Competency)`
  - `(Competency)-[:HAS_ACTIVITY_INDICATOR]->(ActivityIndicator)`
  - `(ActivityIndicator)-[:HAS_ELEMENT]->(CompetencyElement)`

Example confirms the current canonical identity field in graph nodes is `id`, and human-readable display fields are `name` or `text`.

## Locked Decisions

These decisions are confirmed and should be treated as fixed for Step 4:

1. API keeps catalog fields as `key` and `label` (do not expose `{id, name}` directly).
2. Competency detail includes base fields only in this step.
3. Occupation detail includes linked competencies immediately.
4. `CompetencyElement.object` is not part of the official node contract.
5. Graph uses `ekr_level` snake_case (no API mapping layer needed for this field name).
6. `code` is required to be unique where defined in the model, and `CompetencyElement.type` allowed values are enforced at ingest/import time.

## Design Goals for Step 4

1. Define a stable API contract for frontend lookup and detail views.
2. Make catalog behavior deterministic, explicit, and testable.
3. Support current and near-term profile setup needs:
- occupation picker for seeker profile (`occupation_key`)
- competency picker for seeker profile and recruiter requirements (`competency_key`)
4. Keep scope aligned with MVP:
- read-only catalog lookup
- no matching logic
- no semantic expansion / related-competency inference
- no external source runtime calls

## Contract Decision: Graph Fields vs API Fields

Current phase plan uses `competency_key` and display `label` language. Your graph currently uses `id` and `name`/`text`.

To avoid coupling frontend/contracts to internal graph property naming, this plan standardizes API output fields while mapping from your graph source fields:

- API `key` maps from node `id`
- API `label` maps from node `name`

For SQLite relations:

- `occupation_key` stores `Occupation.id`
- `competency_key` stores `Competency.id`

No Neo4j internal numeric node IDs are stored or exposed.

## Proposed Scope for Step 4

### Included

- competency catalog search and competency detail endpoints
- occupation catalog search and occupation detail endpoints
- auth protection for catalog endpoints (JWT-based)
- structured 404/422/401 behavior consistent with current global error format

### Not Included

- profile creation/edit endpoints (step 6)
- recruiter job offer endpoints (step 7)
- matching/explanation/application logic
- write operations against Neo4j from API routes

## API Contract Plan

### 1) Competency Search

`GET /competencies?query=<string>&limit=<int>`

Response:

- list of items with minimal stable shape:
  - `key`
  - `label`
- `code`
- `ekr_level`

Behavior:

- case-insensitive partial search against competency identifiers and display names
- deterministic ordering
- bounded limit with default and max values
- empty list when no matches

### 2) Competency Detail

`GET /competencies/{competency_key}`

Response base shape:

- `key`
- `label`
- `code`
- `ekr_level`

Behavior:

- exact key lookup
- 404 on unknown key
- no similarity fallback

### 3) Occupation Search

`GET /occupations?query=<string>&limit=<int>`

Response:

- list of `{ key, label }` where:
  - `key = Occupation.id`
  - `label = Occupation.name`

### 4) Occupation Detail

`GET /occupations/{occupation_key}`

Response base shape:

- `key`
- `label`
- `required_competencies: [{ key, label }]`

## Backend Module and Layer Plan

Add a dedicated module:

`backend/app/modules/catalog/`

Planned files:

- `router.py`:
  - endpoint declarations
  - auth dependencies
  - request parameter parsing
  - response model wiring
- `schemas.py`:
  - Pydantic request/response models for catalog APIs
- `service.py`:
  - catalog lookup and transformation rules
  - not responsible for auth and not responsible for HTTP wiring
- `repository.py` (recommended):
  - Neo4j read queries isolated from service orchestration logic

Route aggregation:

- include catalog router in `backend/app/api/routes.py`

This keeps route handlers thin and aligns with AGENTS.md boundaries.

## Neo4j Query Strategy (Plan-Level)

1. Open Neo4j session via existing driver accessor.
2. Use read transactions only.
3. Query nodes by explicit labels and expected properties.
4. Return only contract-needed fields.
5. Normalize result payload in service layer.

Guardrails:

- no unconstrained graph traversals for list/search endpoints
- avoid returning full graph objects
- avoid mixed-source logic (no SQLite fallback for catalog display data)
- do not include `ActivityIndicator` or `CompetencyElement` in Step 4 API payloads

## Error and Validation Behavior

Use existing application error contract:

- 401 when token missing/invalid
- 404 for unknown `competency_key` / `occupation_key`
- 422 for invalid query params

Error payload format must remain:

- `error`
- `details[]`

## Security and Privacy Rules for Step 4

Even though catalog is read-only, keep server-side auth checks:

- authenticated users only (both roles allowed)
- no user-specific private data returned
- no recruiter-only or seeker-only restriction needed for catalog reads

This keeps request handling aligned with privacy-first backend enforcement from `AGENTS.md`.

## Testing Plan

### API tests

1. Auth required for all catalog endpoints.
2. Search returns deterministic response shape.
3. Unknown keys return 404 structured error.
4. Empty matches return 200 with empty list.
5. Response payload never includes Neo4j internal IDs.

### Service tests

1. Graph-to-API field mapping:
- `id -> key`
- `name -> label` (for occupations and competencies)
2. Occupation detail includes `required_competencies`.
3. `code` uniqueness assumptions are respected by query behavior.
4. Ordering/limit rules are stable.

### Regression expectations

- existing auth tests remain green
- health endpoint remains unchanged

## Implementation Order

1. Implement catalog schemas and service/repository interfaces based on the locked decisions.
2. Implement competency endpoints (search + detail).
3. Implement occupation endpoints (search + detail).
4. Wire router into global API router.
5. Add API + service tests for contract and error behavior.
6. Update phase plan checklist/status after tests pass.

## Acceptance Criteria

Step 4 is complete when:

1. Backend exposes read-only catalog endpoints for competencies and occupations.
2. Frontend can use returned keys directly as SQLite reference keys.
3. No direct frontend Neo4j access is required.
4. Contract is stable, documented, and covered by tests.
5. Behavior stays deterministic and explainable.

## Recommended Graph Contract Refinements

To make Step 4 and later phases safer and easier:

1. Keep node `id` globally stable and immutable.
2. Make `code` unique for `Competency` and `ActivityIndicator`.
3. Keep `CompetencyElement.type` constrained to known values.
4. Keep `CompetencyElement.object` out of the official contract unless a future step explicitly introduces it.
5. Consider adding indexes/constraints on:
- `Occupation(id)`
- `Competency(id)`
- `ActivityIndicator(id)`
- `CompetencyElement(id)`
