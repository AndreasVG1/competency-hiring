# Phase 1 Step 8 Detailed Plan: Frontend Foundations

## Summary

This document expands step 8 from `docs/phase-1-profile-setup-plan.md` into an implementation-ready frontend plan.

Goal for this step:

- initialize frontend architecture for Phase 1 profile flows
- add Vue Router and role-aware guarded route structure
- add a small auth store using Pinia
- add a typed API client layer so UI components stay free of HTTP details
- establish seeker and recruiter protected areas as stable extension points for steps 9-11

This step is intentionally foundation-only:

- no registration/login form implementation yet (step 9)
- no seeker profile UI yet (step 10)
- no recruiter job profile UI yet (step 11)
- no startup `/auth/me` session restoration yet (step 9)

## Alignment with AGENTS.md

This plan follows repository rules and product principles:

- modular monolith and clear boundaries are preserved
- frontend talks only to backend APIs
- business logic remains server-side, not embedded in UI components
- role and privacy boundaries are enforced in route guards and backend auth checks
- solution stays simple and explicit for MVP scope

## Current Context

Current frontend state:

- Vite + Vue + TypeScript skeleton exists
- app currently mounts a static landing view only
- Vue Router is not installed
- Pinia is not installed
- typed API client modules do not exist

Current backend state relevant for frontend contracts:

- auth endpoints: `/auth/register`, `/auth/login`, `/auth/me`
- protected role-specific endpoints under `/seeker/*` and `/recruiter/*`
- catalog endpoints require auth and are shared by both roles
- backend error format is structured (`error`, `details[]`)

## Locked Decisions (From Planning Discussion)

1. Auth store implementation uses **Pinia**.
2. Step 8 remains **foundation-only** and does not include startup `/auth/me` bootstrap.
3. Wrong-role access redirects to the user’s own protected area.
4. API base URL strategy uses **`VITE_API_BASE_URL`** with localhost default.

## Step 8 Scope

### Included

- install and wire `vue-router` and `pinia`
- create route map with public auth area and two protected role areas
- implement global route guards for auth + role constraints
- create small Pinia auth store contract
- create typed API configuration and client wrapper
- create typed API domain clients (auth, catalog, seeker, recruiter) as foundation modules

### Not Included

- real auth page UI and forms
- real seeker/recruiter feature pages
- session restore call to `/auth/me` on startup
- new backend endpoints or backend schema changes

## Routing and Navigation Plan

### Route groups

- Public auth routes:
  - `/auth/login`
  - `/auth/register`
- Protected seeker area:
  - `/seeker`
- Protected recruiter area:
  - `/recruiter`

### Route meta contract

Each route defines explicit access metadata:

- `requiresAuth: boolean`
- `allowedRoles?: UserRole[]`

### Guard behavior

1. If route is protected and no authenticated user/token exists:
- redirect to `/auth/login`
2. If route is protected and user role is not allowed:
- redirect seekers to `/seeker`
- redirect recruiters to `/recruiter`
3. If route is allowed:
- continue navigation

This keeps role boundaries explicit and predictable without duplicating business rules in many view components.

## Auth Store Plan (Pinia)

Use a small auth store only for session-related state.

### State

- `accessToken: string | null`
- `currentUser: AuthenticatedUser | null`

### Getters

- `isAuthenticated`
- `role`

### Actions

- `setSession(authResponse)`
- `clearSession()`

### Storage behavior in step 8

- define token/session storage helper support
- do not run startup `/auth/me` restoration yet
- actual restore flow is implemented in step 9

## Typed API Client Plan

### API config

- add one typed config module for API base URL resolution
- source from `import.meta.env.VITE_API_BASE_URL`
- fallback default: `http://localhost:8000`

### Shared HTTP layer

Create one reusable client wrapper:

- centralize `fetch` calls
- attach `Authorization: Bearer <token>` when available
- parse JSON responses with types
- normalize backend structured errors into a typed frontend error object

### Domain client modules

Add small typed modules for:

- `authClient`
- `catalogClient`
- `seekerClient`
- `recruiterClient`

Purpose in step 8:

- define stable transport interfaces
- keep components free from URL/header/error parsing details

## Interfaces and Types Added in Frontend

### Core auth types

- `UserRole = "job_seeker" | "recruiter"`
- `AuthenticatedUser`
- `AuthTokenResponse`

### Error types

- structured API error payload type that matches backend:
  - `error: string`
  - `details: [{ field?: string, message: string }]`

### Router typing

- typed route meta for `requiresAuth` and `allowedRoles`

## File and Structure Plan

Planned frontend structure for this step:

- router module for route definitions and guard registration
- store module for auth state (`Pinia`)
- api module with config + shared HTTP client + domain clients
- placeholder views/layouts for:
  - login/register area
  - seeker area
  - recruiter area

Keep this structure minimal and easy to extend in steps 9-11.

## Implementation Order

1. Install `vue-router` and `pinia`.
2. Wire router and pinia into app bootstrap.
3. Add route definitions and placeholder protected areas.
4. Implement global auth/role route guard.
5. Add Pinia auth store with typed state/getters/actions.
6. Add API config and typed shared HTTP client.
7. Add typed domain client modules.
8. Run type-check/build and verify guard behavior manually.

## Test Plan for Step 8

### Build and static checks

- `npm run type-check`
- `npm run build`

### Manual checks

1. Logged-out access to `/seeker` redirects to `/auth/login`.
2. Logged-out access to `/recruiter` redirects to `/auth/login`.
3. Logged-in seeker access to recruiter area redirects to `/seeker`.
4. Logged-in recruiter access to seeker area redirects to `/recruiter`.
5. Correct-role access to own protected area is allowed.
6. API client sends bearer header when token is present.
7. API client exposes normalized structured errors to callers.

## Acceptance Criteria

Step 8 is complete when:

1. frontend app uses Vue Router and Pinia successfully
2. seeker and recruiter protected areas exist and are route-guarded
3. auth and role guard behavior is deterministic and consistent
4. typed API client layer is available and used as the foundation for future UI work
5. no business logic is moved into frontend components
6. step remains strictly foundational, with feature UI deferred to next steps

## Assumptions and Defaults

- backend remains reachable at `http://localhost:8000` by default
- environment-specific base URL is supplied via `VITE_API_BASE_URL` when needed
- backend path prefixes remain as currently implemented (`/auth`, `/seeker`, `/recruiter`, catalog routes)
- session bootstrap via `/auth/me` is intentionally deferred to step 9

