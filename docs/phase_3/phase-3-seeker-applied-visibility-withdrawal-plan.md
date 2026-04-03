# Phase 3 Step 11: Seeker Applied Visibility + Application Withdrawal (Detailed Plan)

## Goal

Implement seeker-facing application status visibility and consent withdrawal so that:

- a seeker can clearly see which published offers they have already applied to
- a seeker can filter marketplace results by application state
- a seeker can withdraw a previously submitted application
- recruiter visibility updates automatically because withdrawn applications are deleted

This step extends existing Phase 2/3 application and consent flows without changing matching logic.

## Why This Step Exists

Current seeker UX has a gap:

- apply state is only tracked locally in the detail view session (`hasApplied`) and is not fetched from backend
- marketplace cards and marketplace filtering do not expose application state
- seekers cannot currently withdraw consent once an application is submitted

This step improves transparency and user control while preserving MVP constraints in `AGENTS.md`:

- privacy and user control
- explicit consent
- deterministic behavior
- thin routes and service-centered business logic

## Scope Boundaries

### In scope

- backend response contract extensions for seeker marketplace list/detail to include application state
- backend query filtering by applied status
- backend seeker-owned delete endpoint for applications
- frontend applied status display in marketplace cards and offer detail
- frontend tri-state applied filter in marketplace
- frontend withdrawal action in seeker offer detail
- backend/frontend tests for visibility, ownership, and withdrawal effects

### Out of scope

- recruiter-facing UI changes
- matching algorithm changes
- snapshot schema changes
- soft-delete/archive application lifecycle
- bulk withdrawal actions from marketplace list

## Decisions Locked for This Step

1. Re-apply policy:
- seeker **can re-apply** after withdrawal (new application + new snapshots)

2. Delete endpoint shape:
- `DELETE /api/v1/seeker/applications/{application_id}`

3. Marketplace filter mode:
- tri-state filter with `All`, `Applied`, `Not applied`

4. Withdrawal UI surface:
- action available in seeker offer detail view only (`/seeker/job-offers/{id}`)

## Current Baseline in Repository

- Backend:
  - `POST /api/v1/seeker/job-offers/{job_offer_id}/apply`
  - `GET /api/v1/seeker/applications`
  - no seeker endpoint to delete an application
  - seeker marketplace list/detail contracts do not include applied state
- Frontend:
  - marketplace and detail pages exist
  - detail page uses local `hasApplied` state and infers 409 conflict after apply
  - no persisted applied state in list/detail responses
  - no withdrawal action

## API and Contract Changes

## 1) Extend seeker marketplace list endpoint

### Endpoint

- `GET /api/v1/seeker/job-offers`

### New query parameter

- `applied: bool | None` (optional)
  - `None` (default): all published offers
  - `true`: only offers where current seeker has an application
  - `false`: only offers where current seeker does not have an application

### Response model extension (`PublicJobOfferListItem`)

Add:

- `applied: bool`
- `application_id: int | null`

Behavior rules:

- `applied = true` iff application exists for (`current_seeker.id`, `job_offer.id`)
- `application_id` contains the matching application row id when applied, else `null`
- filtering is applied before pagination to keep `limit/offset` semantics correct

## 2) Extend seeker offer detail endpoint

### Endpoint

- `GET /api/v1/seeker/job-offers/{job_offer_id}`

### Response model extension (`PublicJobOfferDetail`)

Add:

- `applied: bool`
- `application_id: int | null`

Behavior rules:

- values are computed for current seeker exactly as in list endpoint
- keeps published-only visibility behavior unchanged

## 3) Add seeker application withdrawal endpoint

### Endpoint

- `DELETE /api/v1/seeker/applications/{application_id}`

### Authorization and ownership

- seeker role required (existing `require_job_seeker`)
- only the owner seeker can delete their own application
- missing/non-owned application returns `404` (privacy-safe ownership behavior)

### Success response

- `204 No Content`

### Data effects

- delete `applications` row
- related `application_snapshots` and `application_matching_snapshots` are removed via existing FK/cascade behavior
- recruiter applicant queries naturally stop returning this withdrawn application

### Re-apply behavior

- after delete, seeker may apply again to same published offer
- unique `(job_offer_id, seeker_user_id)` constraint is no longer blocking once old row is deleted

## Backend Implementation Plan

### Router updates

File:

- `backend/app/modules/seeker/router.py`

Changes:

- add optional `applied` query to `list_marketplace_job_offers(...)`
- pass `current_seeker.id` into list/detail service calls (remove `del current_seeker` for those routes)
- add `DELETE /applications/{application_id}` route

### Schema updates

File:

- `backend/app/modules/seeker/schemas.py`

Changes:

- extend `PublicJobOfferListItem` and `PublicJobOfferDetail` with:
  - `applied: bool`
  - `application_id: int | None`

### Service updates (seeker module)

File:

- `backend/app/modules/seeker/service.py`

Changes:

- update `list_published_job_offers(...)` signature to accept:
  - `seeker_user_id: int`
  - `applied: bool | None`
- join `Application` on `job_offer.id + seeker_user_id` to derive applied status and application id
- apply tri-state filtering logic using join presence/absence
- keep ordering and pagination deterministic
- update `get_published_job_offer_detail_or_404(...)` signature to accept `seeker_user_id: int`
- include applied fields in detail response

### Service updates (applications module)

File:

- `backend/app/modules/applications/service.py`

Changes:

- add `delete_application_for_seeker(db_session, *, seeker_user_id: int, application_id: int) -> None`
- enforce ownership-safe lookup:
  - filter by both `Application.id` and `Application.seeker_user_id`
- raise `HTTPException(404, "...")` when missing/non-owned
- delete row + commit

### Error messaging

New error constant (applications service):

- recommended message: `"Application not found."`

## Frontend Implementation Plan

### Domain types

File:

- `frontend/src/types/domain.ts`

Changes:

- extend `PublicJobOfferListItem` with:
  - `applied: boolean`
  - `application_id: number | null`
- extend `PublicJobOfferDetail` with same fields
- no breaking change for existing fields

### Seeker API client

File:

- `frontend/src/api/seekerClient.ts`

Changes:

- extend `PublishedJobOffersListParams` with `applied?: boolean`
- include `applied` in marketplace query object
- add `deleteApplication(applicationId: number): Promise<void>` calling:
  - `DELETE /api/v1/seeker/applications/{applicationId}`

### Marketplace filter component

File:

- `frontend/src/components/MarketplaceFilterBar.vue`

Changes:

- add tri-state applied filter control (reuse `EnumSelect`)
- emit/update `applied` filter value as string enum in component state:
  - `""` -> all
  - `"applied"` -> applied only
  - `"not_applied"` -> not applied only

### Marketplace page integration

File:

- `frontend/src/views/seeker/SeekerJobOfferMarketplaceView.vue`

Changes:

- add draft/applied filter state + applied filter application state
- map UI state to API query param:
  - `""` -> `undefined`
  - `"applied"` -> `true`
  - `"not_applied"` -> `false`
- include applied status indicator in offer card UI (e.g. `Applied`)
- reset applied filter in clear action
- keep pagination behavior unchanged

### Offer detail page integration

File:

- `frontend/src/views/seeker/SeekerJobOfferDetailView.vue`

Changes:

- replace local-only `hasApplied` derivation with backend-truth from `offer.applied`
- derive current `applicationId` from `offer.application_id`
- apply button shown when not applied
- withdraw button shown when applied
- add `withdrawApplication()` with confirm dialog and API call
- after apply success:
  - set `offer.applied = true`
  - set `offer.application_id = response.id`
- after withdraw success:
  - set `offer.applied = false`
  - set `offer.application_id = null`
- keep private analysis section behavior unchanged

## UX and Copy Constraints

- use explicit consent language for both apply and withdraw actions
- avoid decision-making wording
- clearly indicate that withdrawal removes recruiter visibility for that application
- keep action labels clear:
  - `Apply with consent`
  - `Withdraw application`

## Data Integrity and Privacy Considerations

- withdrawal is a hard delete of consented application record
- recruiter reads applicants from applications + snapshots, so deleted records disappear naturally
- no live recomputation is required for recruiter side
- no private analysis endpoint visibility changes are introduced

## Testing and Verification Plan

## Backend tests

### `backend/tests/test_seeker_api.py`

Add/extend scenarios:

1. marketplace list returns `applied` and `application_id` per row
2. marketplace list with `applied=true` returns only applied offers
3. marketplace list with `applied=false` returns only not-applied offers
4. offer detail includes `applied` and `application_id`
5. delete own application returns `204`
6. delete non-owned/missing application returns structured `404`
7. seeker can re-apply after delete to same offer (new application id)

### `backend/tests/test_seeker_service.py`

Add/extend scenarios:

1. list service computes applied flags correctly
2. tri-state applied filter logic works with published-only scope and pagination
3. detail service computes applied/application_id correctly for current seeker

### `backend/tests/test_application_service.py`

Add scenarios:

1. `delete_application_for_seeker` deletes own row and related snapshots
2. missing/non-owned delete returns `404`
3. re-apply after delete succeeds

### `backend/tests/test_recruiter_api.py`

Add/extend scenario:

1. after seeker withdraws application, recruiter applicants list no longer includes that application

## Frontend checks

From `frontend/`:

- `npm run type-check`
- `npm run build`

Manual scenarios:

1. apply to an offer -> marketplace card shows Applied
2. filter `Applied` shows only applied offers
3. filter `Not applied` hides applied offers
4. detail page shows withdraw action for applied offer
5. withdraw from detail -> status updates immediately, recruiter no longer sees applicant
6. re-apply after withdraw works and status flips back to applied

## Acceptance Criteria

Step is complete when:

1. seeker marketplace list/detail responses include canonical applied status fields
2. seeker marketplace supports tri-state application-state filtering
3. seeker can withdraw own application via dedicated delete endpoint
4. withdrawn application is removed from recruiter applicant visibility
5. seeker can re-apply after withdrawal
6. behavior is covered by backend tests and frontend type-check/build passes

## Assumptions and Defaults

- No DB migration is required for this step.
- Application deletion remains hard-delete (no retention/archive policy introduced).
- Ownership-safe `404` behavior is preferred over revealing existence of foreign application ids.
- This step intentionally keeps withdrawal action in offer detail only.

