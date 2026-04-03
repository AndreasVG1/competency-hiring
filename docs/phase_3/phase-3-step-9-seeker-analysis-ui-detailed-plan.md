# Phase 3 Step 9: Seeker Offer Detail Private Analysis UI (Detailed Plan)

## Goal

Implement Phase 3 step 9 by adding a private analysis section to the seeker offer detail page (`/seeker/job-offers/{id}`) that:

- lets the seeker explicitly run analysis on demand
- fetches private analysis from the existing backend endpoint
- displays the current analysis result as formatted JSON
- keeps language and behavior decision-supporting (not decision-making)

This step is intentionally frontend-focused and does not introduce a dedicated explanation-rendering module yet.

## Why This Step Exists

Phase 3 already provides deterministic matching and a private analysis backend endpoint. Step 9 makes that capability usable in the seeker UI while preserving core product rules:

- private analysis remains visible only to the seeker
- analysis is transparent (raw JSON shown without hidden transformations)
- flow remains consent-aware (running analysis is separate from applying)

This aligns with `AGENTS.md` principles:

- transparency over complexity
- privacy and user control
- exact-match MVP logic
- clear business boundaries (backend logic stays in backend, frontend only presents API output)

## Scope Boundaries

### In scope for Step 9

- add frontend domain types for private matching analysis payload
- add seeker API client method for private analysis endpoint
- add a reusable JSON payload viewer component for current and future use
- add a new "Private analysis" section in seeker offer detail view
- support robust loading/error/success UI states
- keep apply flow behavior unchanged

### Out of scope for Step 9

- backend scoring or contract changes
- explanation module that converts payload into human-friendly explanation blocks
- recruiter matching display implementation (covered by later step)
- algorithm/versioning changes
- persistence of private analysis history

## Current Baseline in Repository

- Backend endpoint exists: `GET /api/v1/seeker/job-offers/{job_offer_id}/analysis`.
- Backend response model exists: `MatchingResultPayload` in `backend/app/modules/matching/schemas.py`.
- Seeker detail UI exists in `frontend/src/views/seeker/SeekerJobOfferDetailView.vue`.
- `seekerClient` currently supports:
  - listing offers
  - reading offer detail
  - applying to offer
- frontend domain types currently include recruiter-side snapshot matching but not seeker private analysis payload typing.

## API and Type Contract for This Step

### Endpoint used (existing)

- `GET /api/v1/seeker/job-offers/{job_offer_id}/analysis`

No backend route change is required.

### Frontend type additions

Add typed structures in `frontend/src/types/domain.ts` mirroring current backend response shape:

- `MatchingTotals`
- `MatchingWeightsUsed`
- `MustHaveCoverage`
- `MatchingBreakdownItem`
- `MissingCompetencyItem`
- `InsufficientCompetencyItem`
- `DevelopmentTargetItem`
- `PrivateMatchingAnalysisResponse`

Type alignment rules:

- keep enum-like fields as string literal unions where practical (for stronger TS safety)
- use `RequirementPriority` and `CompetencyLevel` where applicable
- keep `scope` as backend-provided string, no frontend rewriting

### API client addition

Add method in `frontend/src/api/seekerClient.ts`:

- `getPrivateJobOfferAnalysis(jobOfferId: number): Promise<PrivateMatchingAnalysisResponse>`

Implementation rule:

- use existing `apiRequest` utility
- preserve existing auth/error handling behavior

## UI Design and Behavior (Step 9)

## 1) Reusable JSON viewer component

Create a generic component in `frontend/src/components/` (example: `JsonPayloadViewer.vue`) with props:

- `payload: unknown | null`
- `title?: string`
- `emptyText?: string`

Behavior:

- when payload is available: render formatted JSON using `JSON.stringify(payload, null, 2)` inside semantic `<pre><code>`
- when payload is null: render `emptyText`
- do not modify or reorder payload keys in component logic

Reusability requirement:

- keep component generic (not seeker-specific), so later recruiter screens can reuse it for snapshot payload display

## 2) Seeker detail page integration

In `SeekerJobOfferDetailView.vue`, add a new section between "Requirements" and "Apply":

- section title: `Private analysis`
- helper text: clarify analysis is private and decision-supporting
- action button: `Run private analysis`

Interaction flow:

1. seeker opens offer detail page
2. analysis section is visible for valid offer
3. analysis request starts only when button is clicked and confirmation is given(manual trigger, ConfirmDialogHost.vue, explain explicitly, that this is a private analysis and recruiter will not see the result)
4. while loading, button is disabled and label shows loading state
5. on success, render formatted JSON payload in reusable viewer
6. on error, show `ApiErrorNotice` in section

State rules:

- analysis state resets when a different offer id is loaded
- running analysis does not auto-apply and does not alter apply state
- repeated runs are allowed and should replace displayed payload with latest response

## 3) UX copy constraints

All user-facing text in this step must avoid implying automated hiring decisions.

Preferred phrasing style:

- "private analysis"
- "decision support"
- "review the result before deciding whether to apply"

Avoid:

- "you are accepted/rejected"
- "system decides"

## File-Level Implementation Plan

### File 1: `frontend/src/types/domain.ts`

Add private analysis response types and nested types used by seeker view and API client.

### File 2: `frontend/src/api/seekerClient.ts`

- import new private analysis response type
- add `getPrivateJobOfferAnalysis(jobOfferId)` method

### File 3: `frontend/src/components/JsonPayloadViewer.vue` (new)

- add reusable pretty JSON display component
- keep component dependency-free and presentational

### File 4: `frontend/src/views/seeker/SeekerJobOfferDetailView.vue`

- add analysis section markup and button
- add state:
  - `analysisResult`
  - `isAnalysisLoading`
  - `analysisError`
- implement `runPrivateAnalysis()` using `seekerClient.getPrivateJobOfferAnalysis(...)`
- reset analysis state in `loadOffer()`

### File 5: `frontend/src/styles.css`

Add minimal reusable styles for JSON block readability and responsiveness, e.g.:

- bordered container
- readable monospace block
- horizontal scroll for long lines
- spacing aligned with existing section styles

Keep style changes small and consistent with existing design language.

## Error Handling and Edge Cases

### Invalid or missing offer id

- existing offer flow already handles invalid route ids
- analysis action should not execute without a valid loaded offer

### 404 / unpublished offer

- existing not-found handling remains authoritative
- analysis section should not appear in not-found state

### API validation/runtime errors (422, 500, network)

- show `ApiErrorNotice` with existing error parsing behavior
- keep previous successful payload visible only if explicitly desired by implementation choice; default for this step: replace only on successful response and keep last payload otherwise

### Double-click / concurrent runs

- disable run button while request is in-flight
- ignore trigger if already loading

## Testing and Verification Plan

### Static checks

From `frontend/`:

- `npm run type-check`
- `npm run build` (optional but recommended for integration confidence)

### Manual UI scenarios

1. **Happy path**
- open a valid seeker offer detail
- click "Run private analysis"
- confirm loading state and formatted JSON output

2. **Repeated run**
- click "Run private analysis" again
- confirm UI remains stable and payload refreshes

3. **Error path**
- simulate/trigger API error
- confirm `ApiErrorNotice` appears and no app crash occurs

4. **Route change reset**
- navigate to another offer detail
- confirm previous analysis state is cleared for the new offer

5. **Apply non-regression**
- run analysis, then apply
- confirm apply flow and consent messaging remain unchanged

## Acceptance Criteria for Step 9

Step 9 is complete when:

1. seeker can manually trigger private analysis from offer detail page
2. response from existing analysis endpoint is rendered as readable formatted JSON
3. analysis section uses reusable display component suitable for future recruiter reuse
4. errors and loading states are clearly represented without breaking existing page behavior
5. no explanation module parsing/templating logic is introduced in this step
6. UI copy remains decision-supporting and privacy-aware

## Assumptions and Defaults

- backend `MatchingResultPayload` contract remains stable for this step
- manual trigger is preferred over auto-run on page load
- JSON-first presentation is intentionally temporary until dedicated explanation UI is built
- private analysis remains non-persistent in frontend state beyond current view session
