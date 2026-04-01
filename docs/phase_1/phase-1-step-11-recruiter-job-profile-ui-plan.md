# Phase 1 Step 11 Detailed Plan: Recruiter Job Profile UI

## Summary

This document expands step 11 from `docs/phase-1-profile-setup-plan.md` into an implementation-ready frontend plan.

Goal for this step:

- implement the recruiter profile and job-offer setup UI on the protected recruiter route
- let a recruiter manage company profile data
- let a recruiter create and update draft job offers
- let a recruiter add, update, and remove competency requirements with explicit priority values
- reuse Step 10 shared UI components/composables instead of duplicating logic
- keep business rules server-side while frontend remains orchestration/presentation focused

This plan follows `AGENTS.md` constraints:

- frontend communicates only through backend APIs
- backend remains source of truth for ownership/authorization/validation rules
- deterministic and explainable behavior over implicit automation
- strict role boundaries and privacy-safe defaults
- MVP simplicity over broad abstractions

## Current Context

From repository state:

- Step 8 foundations are present:
  - Vue 3 + Vite + TypeScript
  - Vue Router with protected `/seeker` and `/recruiter` routes
  - Pinia auth store and startup bootstrap
  - typed API client layer (`authClient`, `catalogClient`, `seekerClient`, `recruiterClient`)
- Step 9 auth UI is implemented.
- Step 10 seeker profile UI is implemented and introduced reusable frontend blocks:
  - `CatalogSearchPicker.vue`
  - `EnumSelect.vue`
  - `ApiErrorNotice.vue`
  - `useCatalogLabelCache.ts`
- Recruiter backend APIs from Step 7 are implemented:
  - `GET /api/v1/recruiter/profile`
  - `PUT /api/v1/recruiter/profile`
  - `GET /api/v1/recruiter/job-offers`
  - `POST /api/v1/recruiter/job-offers`
  - `GET /api/v1/recruiter/job-offers/{id}`
  - `PATCH /api/v1/recruiter/job-offers/{id}`
  - `GET /api/v1/recruiter/job-offers/{id}/requirements`
  - `POST /api/v1/recruiter/job-offers/{id}/requirements`
  - `PATCH /api/v1/recruiter/job-offers/{id}/requirements/{requirement_id}`
  - `DELETE /api/v1/recruiter/job-offers/{id}/requirements/{requirement_id}`
- Current recruiter view is still a placeholder.

## Locked Decisions

The following decisions are fixed for Step 11:

1. UI shape: single `/recruiter` page with sections, no new recruiter sub-routes.
2. Requirements editing scope: one selected offer at a time.
3. Save behavior for recruiter profile and offer edits: explicit Save buttons (no auto-save).
4. Reuse strategy: directly reuse Step 10 shared components/composable where applicable.
5. Testing depth: `type-check` + `build` + manual browser verification.
6. Missing recruiter profile handling: treat `GET /recruiter/profile` 404 as first-time empty state.

## Step 11 Scope

### Included

- replace recruiter placeholder with real recruiter setup UI
- recruiter/company profile form with explicit save action
- job offer creation flow (title + description)
- job offer list and active offer selection
- active-offer edit flow for draft entries
- requirement add/list/update/delete flows for active offer
- competency picker integration through catalog search
- requirement row label hydration using cache composable
- consistent structured API error rendering

### Not Included

- new recruiter-specific routes (stay on `/recruiter`)
- matching/explanation/application/consent features
- backend API contract changes
- database schema changes
- frontend test framework introduction (Vitest/Cypress/etc.)

## Reuse from Step 10

### 1) `CatalogSearchPicker` (direct reuse)

Use for requirement competency search and selection.

### 2) `EnumSelect` (direct reuse)

Use for requirement priority enum selection:

- `must_have`
- `important`
- `nice_to_have`

### 3) `ApiErrorNotice` (direct reuse)

Use for:

- profile load/save errors
- job-offer load/create/update errors
- requirement add/update/delete row or section errors

### 4) `useCatalogLabelCache` (direct reuse)

Use to hydrate/cache competency labels for requirement rows, with fallback state when label resolution fails.

## Recruiter Page UX and Data Flow

Single page with three sections in this order:

1. Recruiter Profile
2. Job Offers
3. Requirements for Selected Offer

### Recruiter Profile Section

Fields:

- `company_name` (required)
- `contact_name` (required)

Loading behavior:

- fetch profile on page load
- if 200: hydrate form
- if 404: initialize first-time empty form state (not blocking error)
- any other error: show recoverable `ApiErrorNotice`

Save behavior:

- explicit save button triggers `recruiterClient.upsertProfile`
- save/loading state handled in section
- success feedback shown locally
- backend validation errors shown through shared error component

### Job Offers Section

Create flow:

- form fields: `title`, `description`
- submit calls `recruiterClient.createJobOffer`
- on success:
  - prepend offer into local list
  - set created offer as selected active offer
  - clear create form

List and selection flow:

- load via `recruiterClient.listJobOffers`
- show deterministic list of owned draft offers
- allow selecting one active offer for editing and requirement management

Update flow (selected offer only):

- edit title/description in selected-offer form state
- explicit save button calls `recruiterClient.updateJobOffer`
- update list and selected-offer state from response

### Requirements Section (Selected Offer Only)

Activation behavior:

- section disabled/empty when no offer is selected
- on selected offer change, load requirements for that offer

Add flow:

- user searches competency in `CatalogSearchPicker`
- user selects priority in `EnumSelect`
- submit calls `recruiterClient.addRequirement`

Duplicate handling:

- light UI pre-check by `competency_key` against selected-offer requirement rows
- backend `409` remains authoritative and is still surfaced

List/table flow:

- each row displays:
  - competency label (hydrated)
  - competency key
  - priority selector
  - row actions (save priority update, remove)
- priority update calls `recruiterClient.updateRequirement`
- remove calls `recruiterClient.deleteRequirement`

Label strategy:

- render key immediately
- hydrate labels asynchronously through `useCatalogLabelCache`
- fallback states remain explicit (`Loading label...` / `Label unavailable`)

## Interfaces and API Impact

### Backend

No backend changes in Step 11:

- no new endpoints
- no response schema changes
- no migrations

### Frontend

Additions are internal to frontend implementation:

- recruiter view state interfaces for:
  - selected offer state
  - offer create/edit submit states
  - requirement row draft/loading/error states
- no public API client contract changes required

## Architecture and Boundary Rules

1. Keep recruiter view thin:
- orchestrate API calls and local UI state only
- do not move business rules into component logic

2. Keep endpoint access in typed clients:
- no raw `fetch` in views
- no hard-coded endpoint scattering in templates

3. Preserve role/privacy rules:
- recruiter UI calls only recruiter endpoints plus shared catalog endpoints
- backend authz/ownership checks remain authoritative

4. Prefer explicit behavior:
- explicit save actions for profile and offer edits
- avoid implicit auto-save behavior in MVP

## Implementation Order

1. Replace `RecruiterHomeView` placeholder with three-section page shell.
2. Implement recruiter profile load/save with first-time `404` handling.
3. Implement job offer list + create + active selection flow.
4. Implement selected-offer edit flow with explicit save.
5. Implement requirements add/list/update/delete for active offer.
6. Integrate competency label hydration via `useCatalogLabelCache`.
7. Run frontend static checks and manual scenario checklist.
8. Update checklist status in `docs/phase-1-profile-setup-plan.md` only after verification.

## Test Plan

### Static checks

- `npm run type-check`
- `npm run build`

### Manual recruiter flow checks

1. Authenticated recruiter opens `/recruiter` and sees profile + job offers sections.
2. First-time recruiter (profile missing) sees editable empty profile form (not blocking error).
3. Recruiter profile save succeeds with valid data.
4. Invalid profile save shows structured validation errors.
5. Recruiter can create a draft offer with title and description.
6. Recruiter can select an offer and save updates to title/description.
7. Requirement picker search/select + priority adds a row successfully.
8. Duplicate requirement attempt is blocked by UI and/or surfaced backend `409`.
9. Requirement priority update persists correctly.
10. Requirement delete removes row and persists.
11. Requirement competency labels hydrate from catalog and remain stable once cached.
12. Session/auth/API errors are shown clearly through shared API error UI.

### Regression checks

1. Existing auth pages and role routing still function.
2. Seeker `/seeker` Step 10 flows remain unaffected.
3. Shared API client behavior remains unchanged.

## Acceptance Criteria

Step 11 is complete when:

1. `/recruiter` is a functional recruiter profile + draft job-offer management page.
2. Recruiter can create/update own profile through explicit save.
3. Recruiter can create and edit own draft offers.
4. Recruiter can add, edit priority, and remove requirements for selected offer.
5. Requirement input uses catalog-backed search picker and enum priority selector.
6. Error handling is consistent, transparent, and aligned with backend structured errors.
7. Step 10 shared components/composable are reused directly (no duplicate implementations).

## Assumptions and Defaults

- one selected offer at a time is sufficient for Step 11 UX scope
- local in-memory label cache is sufficient for requirement-label hydration
- job offers remain `draft` only in this phase
- no frontend test runner is introduced in this step
- matching/explanation/application/consent and knowledge-adapter features remain out of scope
