# Phase 1 Step 9 Detailed Plan: Authentication UI

## Summary

This document expands step 9 from `docs/phase-1-profile-setup-plan.md` into an implementation-ready plan.

Goal for this step:

- implement production-ready registration and login pages
- let users choose a role (`job_seeker` or `recruiter`) during registration
- persist and restore authenticated session on app startup with `/api/v1/auth/me`
- keep auth and role boundaries explicit and aligned with AGENTS.md
- add the preferred token handling upgrade path for public HTTPS deployment

## Alignment with AGENTS.md

This plan follows repository architecture and product principles:

- frontend communicates only through backend APIs
- backend remains the source of truth for auth and authorization
- route and role boundaries remain explicit (`job_seeker` vs `recruiter`)
- implementation stays MVP-friendly and avoids unnecessary complexity
- privacy and least-privilege behavior stay central

## Current Context

Step 8 already provides:

- Vue Router route structure with role-aware guards
- Pinia auth store with session persistence helpers
- typed API clients including `authClient`
- placeholder auth views to be replaced in this step

Backend contract already provides:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

## Locked Decisions

1. Registration success behavior: auto-login + redirect to role home.
2. Startup restore policy: verify persisted session with `/auth/me` before trusting it.
3. Token handling upgrade path for MVP public deployment: keep short-lived access token in JS-managed state, move refresh token to `HttpOnly Secure SameSite` cookie.

## Step 9 Scope

### Included

- replace auth placeholders with real login/register forms
- registration role selector (`job_seeker` / `recruiter`)
- submit lifecycle (loading, error rendering, success routing)
- startup session bootstrap with `/auth/me` verification
- deterministic routing to role home after successful auth
- prepare frontend and backend contracts for refresh-token cookie flow

### Not Included

- full seeker profile UI (step 10)
- full recruiter job UI (step 11)
- consent/application/matching features
- large auth subsystem redesign beyond targeted cookie upgrade

## Implementation Plan

1. Replace `LoginView.vue` placeholder with a real form bound to `authClient.login`.
2. Replace `RegisterView.vue` placeholder with a real form bound to `authClient.register` and role selection.
3. On successful login/register:
- call auth store `setSession(...)`
- redirect by role (`/seeker` or `/recruiter`)
4. Implement startup bootstrap in `main.ts` (or dedicated auth bootstrap module):
- read persisted auth session
- hydrate store
- call `/auth/me`
- if `/auth/me` fails, clear session and keep user logged out
5. Add bootstrap-ready state handling in auth store if needed (for example `isBootstrapping`) to avoid guard flicker.
6. Normalize and display backend validation/auth errors in both auth forms.
7. Keep forms and views focused on UI concerns only; no business logic in components.

## Token Strategy Upgrade Path (Recommended)

For public HTTPS VPS deployment, apply this incremental upgrade while staying MVP-sized:

1. Access token:
- keep short-lived access token in frontend runtime/session state
- do not persist long-lived bearer tokens in `localStorage`
2. Refresh token:
- move refresh token from JS storage to `HttpOnly` + `Secure` cookie
- use `SameSite=Lax` (or stricter if flow allows)
- limit cookie path to refresh/logout endpoints where possible
3. Refresh flow:
- use `credentials: "include"` for refresh/logout/auth bootstrap calls
- rotate refresh token on every refresh
- revoke on logout
4. CSRF hardening:
- because cookies are auto-sent, add CSRF protection for refresh/logout endpoints (double-submit token or equivalent)
5. Migration approach:
- keep current functionality working first
- introduce cookie-based refresh in a backward-compatible backend update
- remove JS-managed refresh token handling after migration validation

## Interfaces and API Impact

### Frontend

- update auth store/session helpers to support cookie-based refresh transition
- `authClient.refresh()` and `authClient.logout()` should work with cookie-backed refresh flow
- set request credentials policy where needed in shared HTTP client

### Backend (targeted extension, no architecture change)

- refresh and logout endpoints accept refresh token via `HttpOnly` cookie
- register/login may optionally set refresh cookie directly
- `/auth/me` remains bearer-protected and unchanged as user identity source

## Test Plan

### Frontend checks

- `npm run type-check`
- `npm run build`

### Manual auth checks

1. Register as seeker -> redirected to `/seeker`.
2. Register as recruiter -> redirected to `/recruiter`.
3. Login as seeker/recruiter -> redirected to corresponding protected route.
4. Bad credentials and validation errors display meaningful messages.
5. App reload with valid session -> `/auth/me` restores user correctly.
6. App reload with invalid/expired session -> session cleared, user sent to login.
7. Authenticated users visiting `/auth/*` are redirected to their role home.

### Cookie-flow checks

1. Refresh token is not readable in JS.
2. Refresh endpoint works with cookie and rotates token.
3. Logout revokes token and clears cookie.
4. Cross-origin cookie/cors configuration works only for intended frontend origin.

## Acceptance Criteria

Step 9 is complete when:

1. login and registration UIs are fully functional
2. role selection at registration is implemented and enforced in routing behavior
3. startup restore uses `/auth/me` validation before trusting persisted state
4. auth error handling is clear and consistent
5. recommended refresh-token cookie upgrade path is reflected in implementation plan and code direction
6. solution remains within modular monolith and MVP constraints from AGENTS.md

## Assumptions and Defaults

- deployment uses HTTPS on VPS
- frontend and backend origins are known and controlled in environment config
- no microservice split; auth remains in existing backend module
- this step prioritizes secure, incremental improvement over full auth redesign
