# Phase 1 Step 10 Detailed Plan: Seeker Profile UI

## Summary

This document expands step 10 from `docs/phase-1-profile-setup-plan.md` into an implementation-ready frontend plan.

Goal for this step:

- implement the seeker profile setup UI on the protected seeker route
- let a job seeker manage personal profile data and occupation selection
- let a job seeker add, update, and remove competencies with explicit levels
- keep UI logic focused on presentation/orchestration while backend remains source of truth for business rules
- extract targeted reusable UI building blocks that Step 11 can directly reuse

This plan follows `AGENTS.md` constraints:

- frontend talks only to backend APIs
- business rules remain server-side
- deterministic and transparent behavior
- clear role boundaries and privacy-safe defaults
- MVP simplicity over over-engineered abstractions

## Current Context

From the current repository state:

- Step 8 foundations are present:
  - Vue 3 + Vite + TypeScript
  - Vue Router with protected `/seeker` and `/recruiter` areas
  - Pinia auth store and startup bootstrap
  - typed API client layer (`authClient`, `catalogClient`, `seekerClient`, `recruiterClient`)
- Step 9 auth UI is implemented.
- Seeker backend APIs from Step 6 are implemented:
  - `GET /api/v1/seeker/profile`
  - `PUT /api/v1/seeker/profile`
  - `GET /api/v1/seeker/competencies`
  - `POST /api/v1/seeker/competencies`
  - `PATCH /api/v1/seeker/competencies/{id}`
  - `DELETE /api/v1/seeker/competencies/{id}`
- Catalog APIs are available for lookup:
  - `GET /api/v1/catalog/occupations`
  - `GET /api/v1/catalog/occupations/{occupation_key}`
  - `GET /api/v1/catalog/competencies`
  - `GET /api/v1/catalog/competencies/{competency_key}`
- Current seeker view is still a placeholder.

## Locked Decisions

The following decisions are confirmed and fixed for this step:

1. Seeker area shape: single `/seeker` page with profile and competencies sections.
2. Reuse strategy: targeted shared reusable set (not a broad generic form framework).
3. Saved competency label strategy: frontend label hydration via catalog API with local cache.
4. Occupation input mode: search picker.
5. Save behavior: explicit Save button for profile edits.
6. Testing depth: `type-check` + `build` + manual browser verification.
7. Missing profile handling: treat `GET /seeker/profile` 404 as first-time empty state.

## Step 10 Scope

### Included

- replace seeker placeholder with real profile setup UI
- profile form with controlled state and explicit save action
- occupation search/selection via catalog endpoint
- competency search/add flow with level selection
- competency list/table with update-level and delete actions
- targeted reusable frontend components/composables for Step 11 reuse
- clear and structured user-facing error handling

### Not Included

- recruiter job profile UI (Step 11)
- matching/explanation/application/consent features
- backend API contract changes
- database schema changes
- frontend test framework introduction (Vitest/Cypress/etc.)

## Reusable Building Blocks (Step 10 + Step 11)

Create only high-value reusable pieces that map directly to upcoming recruiter UI needs.

### 1) `CatalogSearchPicker` component

Purpose:

- shared lookup UI for competency and occupation selection

Behavior:

- accepts a search function prop
- debounced query input
- shows loading, no-results, and result states
- emits selected item `{ key, label }`
- supports disabled/busy states for submit flows

Step 10 usage:

- occupation picker in profile section
- competency picker in add-competency section

Step 11 reuse:

- competency picker for recruiter requirement management

### 2) `EnumSelect` component

Purpose:

- shared enum selector for small bounded backend enums

Step 10 usage:

- competency `level` selector (`beginner`, `intermediate`, `advanced`)

Step 11 reuse:

- requirement `priority` selector (`must_have`, `important`, `nice_to_have`)

### 3) `ApiErrorNotice` component

Purpose:

- consistent rendering of structured API errors from `ApiClientError`

Behavior:

- renders first error clearly
- optionally supports rendering all messages when provided
- keeps backend error contract visible and transparent

### 4) `useCatalogLabelCache` composable

Purpose:

- hydrate and cache human-readable labels for keys in list/table rows

Behavior:

- in-memory map `key -> label`
- fetches missing competency labels through `catalogClient.getCompetency`
- avoids duplicate requests for already-resolved keys
- exposes fallback state when label resolution fails

## Seeker Page UX and Data Flow

Single page with two sections in this order:

1. Profile section
2. Competency section

### Profile Section

Fields:

- `full_name` (required)
- `summary` (optional)
- `location` (optional)
- `occupation_key` (selected through occupation picker)

Loading behavior:

- fetch profile on page load
- if 200: hydrate form with server data
- if 404: initialize blank first-time form state (not error state)
- any other error: show recoverable error notice

Save behavior:

- explicit save button triggers `seekerClient.upsertProfile`
- save/loading state handled in-section
- success feedback shown locally (non-blocking)
- backend validation errors shown through shared error component

### Competency Section

Add flow:

- user searches competency in picker
- user selects level in enum selector
- submit calls `seekerClient.createCompetency`
- on success: append/refresh row and reset add controls

Duplicate handling:

- UI performs light pre-check against current list by `competency_key`
- backend `409` remains authoritative and is still surfaced if encountered

List/table flow:

- load via `seekerClient.listCompetencies`
- each row displays:
  - label (hydrated via cache)
  - key
  - level selector
  - actions (save level update, remove)
- level update calls `seekerClient.updateCompetency`
- remove calls `seekerClient.deleteCompetency`

Label strategy:

- rows render key immediately
- labels hydrate asynchronously from catalog and cache locally
- unresolved label states remain explicit (loading/fallback text), not hidden

## Interfaces and API Impact

### Backend

No backend changes in Step 10:

- no new endpoints
- no response schema changes
- no migrations

### Frontend

Additions are internal to frontend implementation:

- reusable components: picker, enum selector, API error notice
- small composable for catalog label hydration/cache
- seeker view model state interfaces where needed for row/form state

Public frontend API client contracts remain unchanged.

## Architecture and Boundary Rules

1. Keep route/view components thin:
- orchestrate API calls and UI states only
- avoid embedding domain business rules

2. Keep API handling in typed clients:
- no raw `fetch` in view components
- no endpoint string scattering in UI templates

3. Preserve role/privacy guarantees:
- seeker view only consumes seeker endpoints and shared catalog endpoints
- authorization remains enforced by backend and route guards

4. Favor explicit code paths:
- simple composables and focused components
- avoid speculative generic abstractions

## Implementation Order

1. Create reusable UI primitives/composables (`CatalogSearchPicker`, `EnumSelect`, `ApiErrorNotice`, `useCatalogLabelCache`).
2. Replace `SeekerHomeView` placeholder with real two-section page shell.
3. Implement profile loading and empty-state-on-404 behavior.
4. Implement profile save flow with explicit submit handling.
5. Implement competency add/list/update/delete flows.
6. Integrate catalog label hydration for competency rows.
7. Run frontend static checks and manual scenario checklist.
8. Update checklist status in `docs/phase-1-profile-setup-plan.md` only after verification.

## Test Plan

### Static checks

- `npm run type-check`
- `npm run build`

### Manual seeker flow checks

1. Authenticated seeker opens `/seeker` and sees profile + competency sections.
2. First-time seeker (profile missing) sees editable empty profile form (not blocking error).
3. Profile save succeeds with valid data.
4. Invalid profile save shows structured validation errors.
5. Occupation picker search/select saves correct `occupation_key`.
6. Competency picker search/select + level adds a row successfully.
7. Duplicate competency attempt is blocked by UI and/or returns surfaced backend `409`.
8. Competency level update persists correctly.
9. Competency delete removes row and persists.
10. Competency labels hydrate from catalog and remain stable once cached.
11. Session/auth errors are shown clearly through shared API error UI.

### Regression checks

1. Existing auth pages and role routing still function.
2. Recruiter route remains unaffected by seeker UI changes.
3. Shared API client behavior remains unchanged.

## Acceptance Criteria

Step 10 is complete when:

1. `/seeker` is a fully functional profile setup page (no placeholder).
2. Seeker can create/update personal profile data through explicit save.
3. Seeker can add, edit level, and remove competencies.
4. Occupation and competency inputs use catalog-backed search pickers.
5. Saved competency list is clearly presented with human-readable labels and keys.
6. Error handling is consistent, transparent, and aligned with backend structured errors.
7. Reusable components/composables created in Step 10 are directly reusable in Step 11.

## Assumptions and Defaults

- No frontend test runner is introduced in this step.
- Local in-memory label cache is sufficient for Step 10/11 scope.
- Full i18n/localization and advanced accessibility enhancements can be layered in later phases.
- Matching/explanation/application/consent and knowledge-adapter features remain out of scope.
