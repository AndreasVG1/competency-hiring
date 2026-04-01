# Phase 1 Step 6 Detailed Plan: Seeker Profile Backend

## Summary

This document expands step 6 from `docs/phase-1-profile-setup-plan.md` into an implementation-ready plan for seeker profile backend work.

Goal for this step:

- implement seeker profile create/read/update behavior
- implement seeker competency add/update/list/remove behavior
- keep route handlers thin and business rules in service-layer code
- enforce strict role and ownership boundaries (`job_seeker` only, own records only)
- validate `occupation_key` and `competency_key` against Neo4j catalog data before SQLite writes

This design follows `AGENTS.md` and `neo4j_graph_structure.md`:

- modular monolith structure
- SQLite for business data, Neo4j for catalog lookup truth
- deterministic and explainable behavior
- privacy and user-control boundaries

## Current Context

From current backend state:

- Authentication and role dependencies are implemented (`require_job_seeker`, `require_recruiter`).
- Catalog read APIs are implemented and map Neo4j node identifiers to API `key` fields.
- SQLite tables and enums already exist for:
  - `job_seeker_profiles`
  - `job_seeker_competencies`
  - `CompetencyLevel` (`beginner`, `intermediate`, `advanced`)
- Step 6 APIs are listed in the phase plan but not yet implemented.

No schema migration is required for Step 6.

## Locked Decisions for Step 6

1. `PUT /seeker/profile` uses upsert behavior (create if missing, update if existing).
2. `occupation_key` and `competency_key` are validated on write against Neo4j data.
3. Duplicate competency creation via `POST /seeker/competencies` returns `409` conflict.

## Public API Contract

### 1) Seeker Profile Read

`GET /seeker/profile`

Behavior:

- available to authenticated `job_seeker` users only
- returns current user profile only
- returns `404` when profile does not exist

### 2) Seeker Profile Upsert

`PUT /seeker/profile`

Request body:

- `full_name` (required)
- `summary` (optional)
- `location` (optional)
- `occupation_key` (optional)

Behavior:

- creates profile if missing
- updates existing profile if present
- validates `occupation_key` against catalog (`Occupation.id`) when provided
- returns `404` on unknown occupation key

### 3) Seeker Competency List

`GET /seeker/competencies`

Behavior:

- returns competencies for current user only
- deterministic ordering (by `id ASC`)

### 4) Seeker Competency Add

`POST /seeker/competencies`

Request body:

- `competency_key` (required)
- `level` (`beginner | intermediate | advanced`)

Behavior:

- validates `competency_key` against catalog (`Competency.id`)
- inserts competency row for current user
- returns `409` if same `competency_key` already exists for the user

### 5) Seeker Competency Update

`PATCH /seeker/competencies/{id}`

Request body:

- `level` (`beginner | intermediate | advanced`)

Behavior:

- updates `level` only
- enforces ownership by querying with both competency `id` and `current_user.id`
- returns `404` if not found for current user

### 6) Seeker Competency Remove

`DELETE /seeker/competencies/{id}`

Behavior:

- deletes competency only if it belongs to current user
- returns `404` if not found for current user
- returns `204 No Content` on success

## Module and Layer Plan

Add a new module:

`backend/app/modules/seeker/`

Planned files:

- `router.py`
  - endpoint declarations
  - auth dependency wiring (`require_job_seeker`)
  - request/response model wiring
- `schemas.py`
  - request and response models for seeker profile and competencies
- `service.py`
  - business rules, ownership checks, and orchestration
  - profile upsert and competency CRUD operations
- `__init__.py`

Router wiring:

- include seeker router in `backend/app/api/routes.py`

Boundary rules:

- no business logic in route handlers
- no direct frontend-to-db behavior assumptions
- no matching/explanation logic in this step

## Catalog Validation Strategy

Validation happens server-side in the seeker service:

- `occupation_key` validation:
  - call catalog lookup by key and reject unknown keys
- `competency_key` validation:
  - call catalog lookup by key and reject unknown keys

Notes:

- use catalog service/repository access patterns already established
- do not persist Neo4j internal IDs
- store only stable graph keys in SQLite relations

## Error and Validation Behavior

Use existing global error format:

- HTTP errors -> `error: "http_error"` with `details[]`
- request validation errors -> `error: "validation_error"` with `details[]`

Expected status patterns:

- `401` for missing/invalid JWT
- `403` for authenticated recruiter trying seeker endpoints
- `404` for missing profile/competency or unknown catalog key
- `409` for duplicate competency add
- `422` for invalid payload/enums

## Test Plan

Add `backend/tests/test_seeker_api.py`:

1. all seeker endpoints require authentication
2. recruiter token is forbidden on seeker endpoints
3. profile `GET` returns `404` before profile creation
4. profile `PUT` creates profile when missing
5. profile `PUT` updates existing profile (upsert update path)
6. unknown `occupation_key` in profile write returns structured `404`
7. competency `POST` creates row for current seeker
8. duplicate competency `POST` returns structured `409`
9. invalid `level` returns `422`
10. competency list returns only current seeker records
11. competency `PATCH` updates level for own record
12. competency `PATCH` returns `404` for non-owned/missing record
13. competency `DELETE` removes own record and returns `204`
14. competency `DELETE` returns `404` for non-owned/missing record

Add `backend/tests/test_seeker_service.py`:

1. profile upsert create path
2. profile upsert update path
3. occupation key validation behavior
4. competency key validation behavior
5. duplicate competency conflict path
6. ownership-safe update and delete behavior

Regression expectation:

- existing auth and catalog tests remain green.

## Implementation Order

1. Create seeker schemas and service interfaces.
2. Implement profile read/upsert logic with occupation key validation.
3. Implement competency list/add/update/delete with ownership and duplicate checks.
4. Add seeker router and wire into API routes.
5. Add API and service tests.
6. Run backend tests and update step checklist in `docs/phase-1-profile-setup-plan.md` only after passing coverage.

## Acceptance Criteria

Step 6 is complete when:

1. seeker profile and competency endpoints are implemented and wired
2. only `job_seeker` users can access these routes
3. seeker can only operate on own profile and competencies
4. competency levels are enum-validated
5. catalog key validation prevents unknown occupation/competency references
6. behavior is covered by API + service tests and follows structured error contracts
