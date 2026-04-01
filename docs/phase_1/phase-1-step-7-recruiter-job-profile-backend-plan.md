# Phase 1 Step 7 Detailed Plan: Recruiter Job Profile Backend

## Summary

Implement Step 7 as the recruiter-side counterpart of Step 6, while using light reuse to avoid MVP over-abstraction.

This keeps `AGENTS.md` constraints intact:
- modular monolith
- thin routers
- service-owned business rules
- deterministic behavior
- strict role/ownership/privacy boundaries

## Current Context

From current backend state:
- Authentication and role dependencies are implemented (`require_job_seeker`, `require_recruiter`).
- Catalog read APIs are implemented and already used for server-side key validation patterns.
- SQLite tables and enums already exist for:
  - `recruiter_profiles`
  - `job_offers`
  - `job_offer_requirements`
  - `RequirementPriority` (`must_have`, `important`, `nice_to_have`)
  - `JobOfferStatus` (`draft`)
- Seeker backend step (Step 6) is implemented with service-layer ownership checks and thin router wiring, which is the direct reference pattern for this step.

No schema migration is required for Step 7.

## Locked Decisions for Step 7

1. `PUT /recruiter/profile` uses upsert behavior (create if missing, update if existing).
2. `POST /recruiter/job-offers` always stores `status=draft` server-side.
3. `PATCH /recruiter/job-offers/{id}` allows editing draft fields only (`title`, `description`) and does not support status transitions in this step.
4. Requirement write operations validate `competency_key` against catalog data before SQLite writes.
5. Duplicate requirement creation (`job_offer_id + competency_key`) returns `409` conflict.
6. Non-owned or missing job offer/requirement operations return `404` (ownership-safe behavior, same pattern as Step 6).
7. List endpoints use deterministic ordering (`id ASC`).
8. Reuse approach is light: mirror Step 6 module/service/router pattern and share only test helpers/constants where beneficial; avoid generic CRUD abstraction layers.

## Public API Contract

### 1) Recruiter Profile Read

`GET /recruiter/profile`

Behavior:
- available to authenticated `recruiter` users only
- returns current recruiter profile only
- returns `404` when profile does not exist

### 2) Recruiter Profile Upsert

`PUT /recruiter/profile`

Request body:
- `company_name` (required)
- `contact_name` (required)

Behavior:
- creates profile if missing
- updates existing profile if present

### 3) Recruiter Job Offer List

`GET /recruiter/job-offers`

Behavior:
- returns job offers for current recruiter only
- deterministic ordering (`id ASC`)

### 4) Recruiter Job Offer Create

`POST /recruiter/job-offers`

Request body:
- `title` (required)
- `description` (required)

Behavior:
- creates a job offer owned by current recruiter
- persists `status=draft` regardless of client input
- returns created draft job offer

### 5) Recruiter Job Offer Read

`GET /recruiter/job-offers/{id}`

Behavior:
- returns job offer only when it belongs to current recruiter
- returns `404` for missing or non-owned offer

### 6) Recruiter Job Offer Update

`PATCH /recruiter/job-offers/{id}`

Request body:
- `title` (optional)
- `description` (optional)

Behavior:
- updates editable draft fields
- ownership is enforced by querying with both offer `id` and `current_user.id`
- returns `404` for missing/non-owned offer
- no publish/archive/status flow in this step

### 7) Job Offer Requirement List

`GET /recruiter/job-offers/{id}/requirements`

Behavior:
- validates ownership of parent job offer first
- returns requirements for that offer only
- deterministic ordering (`id ASC`)

### 8) Job Offer Requirement Add

`POST /recruiter/job-offers/{id}/requirements`

Request body:
- `competency_key` (required)
- `priority` (`must_have | important | nice_to_have`)

Behavior:
- validates job offer ownership
- validates `competency_key` against catalog (`Competency.id`)
- inserts requirement for that offer
- returns `409` if same `competency_key` already exists for that offer

### 9) Job Offer Requirement Update

`PATCH /recruiter/job-offers/{id}/requirements/{requirement_id}`

Request body:
- `priority` (`must_have | important | nice_to_have`)

Behavior:
- validates job offer ownership
- updates `priority` only
- returns `404` for missing/non-owned requirement

### 10) Job Offer Requirement Remove

`DELETE /recruiter/job-offers/{id}/requirements/{requirement_id}`

Behavior:
- validates job offer ownership
- deletes requirement only when it belongs to the owned offer
- returns `404` for missing/non-owned requirement
- returns `204 No Content` on success

## Module and Layer Plan

Add a new module:

`backend/app/modules/recruiter/`

Planned files:
- `router.py`
  - endpoint declarations
  - auth dependency wiring (`require_recruiter`)
  - request/response model wiring only
- `schemas.py`
  - request and response models for recruiter profile, job offers, and requirements
- `service.py`
  - all business rules, ownership checks, and orchestration
  - profile upsert, owned offer CRUD, owned requirement CRUD
  - catalog key validation for requirements
- `__init__.py`

Router wiring:
- include recruiter router in `backend/app/api/routes.py`

Boundary rules (from `AGENTS.md`):
- keep route handlers thin
- keep business logic in services/domain logic
- keep privacy-sensitive ownership checks server-side and auditable
- do not place recruiter business rules in frontend code
- avoid oversized generic helper abstractions

## Duplication Avoidance Strategy (Step 6 -> Step 7)

Use a light-reuse strategy:
1. Mirror the proven Step 6 module shape and error semantics.
2. Reuse naming and control-flow conventions for:
- `_or_404` lookup helpers
- ownership-scoped queries
- commit/refresh persistence flow
3. Extract only small shared test helpers (token creation, auth headers, structured error assertions) into test-level helper utilities if this reduces copy-paste.
4. Do not introduce a cross-module generic CRUD framework in Phase 1 MVP.

This keeps implementation explicit and readable while still reducing avoidable duplication.

## Error and Validation Behavior

Use existing global error format:
- HTTP errors -> `error: "http_error"` with `details[]`
- request validation errors -> `error: "validation_error"` with `details[]`

Expected status patterns:
- `401` for missing/invalid JWT
- `403` for authenticated seeker trying recruiter endpoints
- `404` for missing profile/offer/requirement, unknown `competency_key`, or ownership-protected resources
- `409` for duplicate requirement add
- `422` for invalid payload/enums

## Test Plan

Add `backend/tests/test_recruiter_api.py`:
1. all recruiter endpoints require authentication
2. seeker token is forbidden on recruiter endpoints
3. profile `GET` returns `404` before profile creation
4. profile `PUT` creates profile when missing
5. profile `PUT` updates existing profile
6. job offer `POST` creates a draft offer
7. job offer list/get returns only current recruiter records
8. job offer `PATCH` updates own offer fields
9. job offer `GET`/`PATCH` returns `404` for non-owned or missing offer
10. requirement `POST` creates row for owned offer
11. duplicate requirement `POST` returns structured `409`
12. unknown `competency_key` in requirement write returns structured `404`
13. invalid `priority` returns `422`
14. requirement list returns only requirements for owned offer
15. requirement `PATCH` updates priority for own requirement
16. requirement `PATCH` returns `404` for non-owned/missing requirement
17. requirement `DELETE` removes own requirement and returns `204`
18. requirement `DELETE` returns `404` for non-owned/missing requirement

Add `backend/tests/test_recruiter_service.py`:
1. recruiter profile upsert create path
2. recruiter profile upsert update path
3. job offer create/list/get/update owned-path behavior
4. requirement competency-key validation behavior
5. duplicate requirement conflict behavior
6. ownership-safe requirement update/delete behavior

Regression expectation:
- existing auth, catalog, and seeker tests remain green.

## Implementation Order

1. Create recruiter schemas and service interfaces.
2. Implement recruiter profile read/upsert logic.
3. Implement owned job offer list/create/read/update behavior with draft-only status handling.
4. Implement requirement list/add/update/delete with ownership and duplicate checks.
5. Add recruiter router and wire into API routes.
6. Add API and service tests.
7. Run backend tests and update step checklist in `docs/phase-1-profile-setup-plan.md` only after passing coverage.

## Acceptance Criteria

Step 7 is complete when:
1. recruiter profile, job offer, and requirement endpoints are implemented and wired
2. only `recruiter` users can access recruiter routes
3. recruiter can only operate on own profile, own offers, and own offer requirements
4. requirement priorities are enum-validated
5. unknown competency references are blocked by catalog validation
6. job offers remain draft-only in this phase
7. behavior is covered by API + service tests and follows structured error contracts

## Assumptions and Defaults

- Recruiter account represents a single company context for now.
- Job offer lifecycle beyond `draft` is deferred to later phases.
- Matching/explanation/application/consent-snapshot behavior remains out of scope for Step 7.
- No microservices, eventing, ML ranking, or runtime external-source dependence are introduced.
