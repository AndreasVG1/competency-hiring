# Phase 1 Authentication and Authorization Plan

## Summary

This document expands step 5 from `docs/phase-1-profile-setup-plan.md` into an implementation-ready plan for backend authentication and authorization.

The goal for this phase is deliberately narrow:

- support registration for `job_seeker` and `recruiter`
- support email/password login
- issue JWT bearer tokens for authenticated API access
- resolve the authenticated user on protected endpoints
- enforce role-based access in reusable backend dependencies

This design follows the constraints in `AGENTS.md`:

- keep the system a modular monolith
- keep business rules out of route handlers
- prefer explicit, readable logic over clever abstractions
- preserve privacy and role boundaries from the beginning

It also intentionally stays independent from the skipped competency catalog contract work in step 4, because authentication only depends on SQLite user data and backend request handling.

## Current State

The repository already provides the main prerequisites for implementing auth:

- `users` table exists in SQLite with `email`, `password_hash`, and `role`
- `UserRole` enum already defines `job_seeker` and `recruiter`
- dependencies are already installed for password hashing and JWTs:
  - `passlib[bcrypt]`
  - `python-jose[cryptography]`
- FastAPI app setup, settings loading, DB session creation, and structured error responses already exist

What is still missing:

- no auth module
- no registration/login endpoints
- no current-user dependency
- no reusable role guard dependency
- no auth-specific request/response schemas
- no tests for credentials, tokens, or access control

## Design Goals

### 1. Keep auth simple and explicit

This is an MVP and bachelor thesis project. `AGENTS.md` explicitly prefers simplicity, readability, and controlled scope over architectural sophistication.

For that reason, the implementation should use:

- local email/password authentication
- a single `users` table as the source of truth
- JWT bearer tokens
- server-side role checks in FastAPI dependencies

It should not introduce:

- refresh tokens
- OAuth providers
- session storage
- policy engines
- multi-tenant organization models
- permission matrices beyond the two current roles

### 2. Make authorization reusable for later modules

Step 5 should not only add `/auth/*` endpoints. It should also establish the dependency layer that step 6 and step 7 can reuse directly.

That means the auth module should provide:

- `get_current_user`
- `require_job_seeker`
- `require_recruiter`

This matches `AGENTS.md` guidance to keep business and access rules in service/dependency layers rather than scattering them across route handlers.

### 3. Preserve privacy-sensitive boundaries early

`AGENTS.md` treats privacy and controlled visibility as core product rules. Even though consent and recruiter candidate visibility are later features, the authorization layer should already enforce a strict split between seeker-only and recruiter-only routes.

That means:

- seekers must not call recruiter management routes
- recruiters must not call seeker profile routes
- protected endpoints must derive user identity from the bearer token, not from client-submitted user IDs

## Proposed Module Structure

Add a dedicated auth module under:

```text
backend/app/modules/auth/
```

Recommended files:

- `router.py`
- `schemas.py`
- `service.py`
- `security.py`
- `dependencies.py`

Suggested responsibilities:

### `router.py`

- define `/auth/register`, `/auth/login`, `/auth/me`
- keep handlers thin
- delegate registration/login/current-user behavior to service and dependency functions

### `schemas.py`

- define request/response payloads
- define auth-facing user response models
- keep API contracts explicit and stable

### `service.py`

- create users
- validate credentials
- fetch users by id/email
- centralize auth-related business rules

### `security.py`

- hash passwords
- verify passwords
- create JWTs
- decode and validate JWTs

### `dependencies.py`

- parse bearer token from requests
- resolve authenticated user from DB
- expose role guard dependencies

This structure keeps route handlers thin and aligns with the modular monolith direction from `AGENTS.md`.

## API Plan

### `POST /auth/register`

Purpose:
- create a user account with an explicit role
- return an access token immediately so the frontend can treat registration as sign-in

Request body:

```json
{
  "email": "user@example.com",
  "password": "strong-password",
  "role": "job_seeker"
}
```

Response body:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "role": "job_seeker",
    "created_at": "2026-03-24T12:00:00Z"
  }
}
```

Behavior:

- normalize email for uniqueness checks
- reject duplicate email
- hash password before persistence
- persist only `password_hash`, never raw password
- issue JWT after successful creation

Reasoning:
- returning the token immediately reduces frontend friction for the Phase 1 profile setup flow
- it stays simple while still matching the planned frontend auth store in the phase 1 plan

### `POST /auth/login`

Purpose:
- authenticate an existing user with email/password

Request body:

```json
{
  "email": "user@example.com",
  "password": "strong-password"
}
```

Response body:
- same shape as register

Behavior:

- look up user by normalized email
- verify password against stored hash
- issue JWT on success
- return a generic authentication failure on invalid credentials

Reasoning:
- generic failure text avoids leaking whether an email exists
- JSON payload login fits the current frontend plan better than OAuth2 password form encoding

### `GET /auth/me`

Purpose:
- return the authenticated user represented by the bearer token

Behavior:

- require `Authorization: Bearer <token>`
- decode token
- resolve current user from SQLite
- return user summary

Reasoning:
- this endpoint supports frontend session restoration on app startup, as already planned in Phase 1 step 9

## Request and Response Types

Recommended public types:

```text
UserRole = "job_seeker" | "recruiter"
```

Recommended request models:

- `RegisterRequest`
  - `email: EmailStr`
  - `password: str`
  - `role: UserRole`
- `LoginRequest`
  - `email: EmailStr`
  - `password: str`

Recommended response models:

- `AuthenticatedUser`
  - `id: int`
  - `email: str`
  - `role: UserRole`
  - `created_at: datetime`
- `AuthTokenResponse`
  - `access_token: str`
  - `token_type: str`
  - `user: AuthenticatedUser`

Recommended validation:

- use `EmailStr` for email shape validation
- require non-empty password
- optionally set a minimum password length such as 8 characters

Reasoning:
- these models are small, stable, and enough for the frontend auth store
- explicit response models support the API consistency rules in `AGENTS.md`

## JWT Strategy

Use stateless JWT bearer authentication for this phase.

Recommended token claims:

- `sub`: user id as string
- `role`: current role value
- `exp`: expiration timestamp

Recommended settings additions:

- `jwt_algorithm` with default `HS256`
- `jwt_access_token_expire_minutes` with default `60`

Keep existing:

- `jwt_secret`

Reasoning:

- JWT bearer auth is already the selected direction in the phase 1 plan
- stateless tokens are enough for a small MVP and do not require extra database tables
- adding algorithm and expiry to settings keeps configuration explicit and environment-driven, which matches `AGENTS.md`

Out of scope for now:

- refresh tokens
- token revocation lists
- remember-me sessions
- email verification tokens
- password reset tokens

## Authorization Strategy

Authorization should be enforced through FastAPI dependencies, not inside each route body.

Recommended dependency set:

- `get_current_user`
- `require_role(required_role: UserRole)`
- `require_job_seeker`
- `require_recruiter`

### `get_current_user`

Responsibilities:

- read bearer token from request headers
- decode and validate JWT
- extract `sub`
- load the user from SQLite
- fail if token is missing, invalid, expired, or references a missing user

Return:

- the SQLAlchemy `User` entity or a dedicated auth-domain user object

### `require_role`

Responsibilities:

- accept an authenticated user from `get_current_user`
- compare `user.role` to the required role
- raise `403 Forbidden` on mismatch

Then expose two concrete wrappers:

- `require_job_seeker`
- `require_recruiter`

Reasoning:

- `AGENTS.md` explicitly says role-based access control is in scope
- dependency-based enforcement makes route protection consistent and easy to audit
- later seeker and recruiter routers can attach these dependencies without rewriting auth logic

## Security Rules

The implementation should follow these baseline rules:

- never store plain-text passwords
- never log raw passwords, tokens, or password hashes
- use generic invalid-credential messages
- reject malformed or expired tokens with `401`
- reject wrong-role access with `403`
- derive user identity from the token, not request payloads

These decisions directly support the security and privacy expectations in `AGENTS.md`, especially:

- least privilege
- server-side authorization checks
- predictable visibility rules

## Error Handling

Reuse the existing structured error response format from `backend/app/core/errors.py`.

Recommended status mapping:

- `400` or `409` for duplicate registration email
- `401` for invalid credentials
- `401` for missing, invalid, or expired token
- `403` for valid authentication with wrong role

Recommended auth-facing messages:

- duplicate email: `Email is already registered.`
- invalid credentials: `Invalid email or password.`
- invalid token: `Could not validate credentials.`
- forbidden role: `You do not have permission to access this resource.`

Reasoning:

- consistent structured errors make frontend integration simpler
- separating `401` and `403` keeps authentication and authorization failures clear

## Integration Into Existing App Structure

### Router aggregation

`backend/app/api/routes.py` should evolve from a single-file route definition into a router aggregator.

Recommended shape:

- keep `/health`
- include the auth router under `/auth`
- later include seeker and recruiter routers in the same way

This preserves a clean top-level API assembly point while keeping module logic local to each feature area.

### Settings

Update `backend/app/core/settings.py` to support JWT configuration cleanly:

- `jwt_secret`
- `jwt_algorithm`
- `jwt_access_token_expire_minutes`

This keeps auth behavior environment-configurable without introducing new infrastructure.

### Database access

Use the existing `get_db_session()` dependency and current SQLAlchemy session factory.

No schema migration is required for step 5 because:

- the `users` table already supports the needed fields
- JWT auth is stateless for this phase

## Testing Plan

Add backend tests before moving on to seeker and recruiter feature routes.

Recommended coverage:

### Registration

- creates a `job_seeker` successfully
- creates a `recruiter` successfully
- stores a password hash instead of the raw password
- rejects duplicate email
- rejects invalid role or invalid payload

### Login

- succeeds with correct credentials
- fails with unknown email
- fails with wrong password
- returns bearer token payload in expected format

### Current user

- `/auth/me` returns the authenticated user for a valid token
- `/auth/me` fails without a token
- `/auth/me` fails with malformed token
- `/auth/me` fails with expired token
- `/auth/me` fails when the token refers to a deleted or missing user

### Role authorization

- seeker token is rejected by recruiter-only dependency
- recruiter token is rejected by seeker-only dependency

Reasoning:

- `AGENTS.md` lists authorization and privacy as high-priority test areas
- these tests create the foundation for the later seeker and recruiter routes

## Implementation Order

Recommended order for coding:

1. Add auth schemas and security helpers.
2. Add auth service functions for user lookup, registration, and credential validation.
3. Add current-user and role-check dependencies.
4. Add auth router endpoints.
5. Include the auth router in the main API router.
6. Add tests for register, login, token validation, and role checks.
7. Update docs or environment notes if new settings are introduced.

This order keeps the lower-level auth primitives in place before wiring routes, and it makes test writing straightforward.

## Explicit Non-Goals for This Step

To keep scope aligned with the MVP and `AGENTS.md`, this step should not implement:

- profile creation during registration
- recruiter company membership or invitations
- account verification emails
- password reset flow
- token refresh flow
- recruiter access to seeker data beyond future role-protected routes
- any consent or application-sharing logic

Those concerns belong to later modules and should not be folded into the auth layer prematurely.

## Recommended Defaults

Unless implementation constraints inside the codebase require a small adjustment, use these defaults:

- registration signs the user in immediately
- login and register both return the same auth payload shape
- bearer token type is always `bearer`
- access token expiry defaults to 60 minutes
- role checks are implemented as dedicated dependencies
- `/auth/me` is the canonical way for the frontend to restore session state

These defaults are intentionally conservative, easy to explain, and well aligned with the current Phase 1 scope.
