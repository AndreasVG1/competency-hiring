# Phase 3 Step 10: Recruiter Applicants Shared Matching UI (Detailed Plan)

## Goal

Implement Phase 3 step 10 by extending the recruiter applicants page (`/recruiter/job-offers/{id}/applicants`) so that each applicant card includes the matching result snapshot that was shared at application time.

This step must:

- show matching data only from `shared_matching` snapshot fields returned by backend
- clearly label the data as consent-shared and application-time scoped
- keep output transparent by rendering the stored payload directly as formatted JSON
- keep applicant cards compact by showing analysis payload in a collapsible section
- preserve decision-supporting language (not decision-making language)

## Why This Step Exists

Phase 3 already supports:

- deterministic matching computation
- application-time matching snapshot persistence
- recruiter API response fields containing `shared_matching`

Step 10 closes the frontend visibility gap by exposing that snapshot in recruiter UI, aligned with `AGENTS.md` principles:

- transparency over complexity
- privacy and user control
- clear consent boundary (only after apply)
- deterministic, auditable output presentation

## Scope Boundaries

### In scope for Step 10

- recruiter UI rendering of `shared_matching` data per applicant
- explicit consent/snapshot labeling in recruiter copy
- reuse of Step 9 generic JSON presentation component for payload rendering
- collapsible analysis payload section per applicant (collapsed by default)
- null-safe fallback UI for applicants without a matching snapshot (legacy or transitional rows)

### Out of scope for Step 10

- backend API/schema changes for recruiter applicants endpoint
- matching algorithm changes
- explanation transformation layer that rewrites or interprets payload fields
- seeker-side UI changes
- persistence/model changes

## Current Baseline in Repository

- Recruiter applicants page exists: `frontend/src/views/recruiter/RecruiterJobOfferApplicantsView.vue`.
- Recruiter API client already returns applicants with snapshot matching data:
  - `recruiterClient.listApplicants(jobOfferId)` in `frontend/src/api/recruiterClient.ts`.
- Domain types already include matching snapshot fields:
  - `RecruiterApplicantListItem.shared_matching` and `RecruiterApplicantSharedMatching` in `frontend/src/types/domain.ts`.
- Reusable JSON component from Step 9 already exists:
  - `frontend/src/components/JsonPayloadViewer.vue`.
- Shared JSON styling from Step 9 already exists in:
  - `frontend/src/styles.css` (`.json-payload-viewer`, `.json-payload-block`).

## Reuse Strategy from Step 9

Step 10 should explicitly reuse and not duplicate these assets:

1. `JsonPayloadViewer.vue`
- reuse for rendering `applicant.shared_matching.result_payload`
- keep rendering raw payload with `JSON.stringify(payload, null, 2)` behavior from component

2. Existing matching type definitions in `domain.ts`
- consume `RecruiterApplicantListItem` as-is
- no local `any` or ad-hoc shape assumptions in recruiter view

3. Existing JSON block styles in `styles.css`
- rely on current generic JSON viewer styles
- add only minimal recruiter-page styles if spacing/layout needs adjustment

## UI Design and Behavior (Step 10)

## 1) New section inside each applicant card

Add a new section after "Shared competencies":

- heading: `Shared matching result`
- helper text: `This result was shared at application time as part of consent.`
- render payload inside a collapsible container so cards stay compact

Within the section:

- when `applicant.shared_matching` is present:
  - show summary metadata:
    - `Score`
    - `Algorithm version`
    - `Matching snapshot created at`
  - render full `result_payload` using `JsonPayloadViewer`
  - viewer title example: `Snapshot matching payload`
  - default state: collapsed
  - toggle label example: `Show matching payload` / `Hide matching payload`
  - recommended implementation: semantic `<details><summary>` for native keyboard support and accessibility

- when `applicant.shared_matching` is `null`:
  - show a note such as:
    - `No shared matching snapshot is available for this application.`
  - do not show empty or misleading score fields

## 2) Copy and transparency constraints

All recruiter-facing copy in this step must:

- emphasize consent sharing and snapshot timing
- avoid language that implies automated hiring decisions

Preferred phrasing style:

- "shared at application time"
- "decision-supporting result"
- "stored snapshot"

Avoid:

- "recommended candidate"
- "accept/reject"
- "system decision"

## 3) Data handling rules

- Use backend-provided values directly.
- Do not recompute score on frontend.
- Do not transform payload into derived decision labels.
- Keep each applicant card fully isolated (no cross-card shared matching state).

## File-Level Implementation Plan

### File 1: `frontend/src/views/recruiter/RecruiterJobOfferApplicantsView.vue`

- import `JsonPayloadViewer`
- add `Shared matching result` subsection in applicant card template
- render `shared_matching` metadata fields and formatted payload when available
- wrap payload viewer in a collapsible UI block (collapsed by default)
- render a clear fallback note when `shared_matching` is missing
- keep existing loading/error behavior unchanged

### File 2: `frontend/src/styles.css` (optional, minimal)

Only if needed for readability/spacing:

- add compact utility classes for matching metadata rows in applicant card
- add minimal styles for collapsible summary/toggle affordance
- reuse existing panel/table typography and spacing conventions
- avoid introducing a separate style system for this step

### File 3: `docs/phase_3/phase-3-matching-explanation-plan.md` (optional tracking update)

After implementation, mark step 10 as completed in checklist if project process expects that update.

## Error Handling and Edge Cases

### Missing matching snapshot (legacy rows)

- expected backend state: `shared_matching: null`
- UI behavior: show fallback note, no crash, no placeholder fake values

### Mixed applicant list

- if one applicant has snapshot and another does not, both cards render correctly according to their own data

### Invalid timestamp values

- use existing date formatting helper behavior
- if parse fails, display raw value as already done in view

### Large payloads

- JSON viewer relies on existing scrollable `<pre>` style
- no truncation in step 10 (full transparency)
- payload remains collapsed by default to reduce visual bloat for long snapshots

## Testing and Verification Plan

### Static checks

From `frontend/`:

- `npm run type-check`
- `npm run build`

### Manual UI scenarios

1. Snapshot available
- open recruiter applicants for an owned offer with at least one applicant
- verify score, algorithm version, and snapshot time are visible
- verify payload is collapsed initially and expands/collapses via toggle

2. Snapshot missing fallback
- verify applicant row with `shared_matching = null` shows fallback note only

3. Mixed rows
- verify list handles both snapshot-present and snapshot-missing cards in same view

4. Accessibility and keyboard interaction
- tab to collapse toggle and activate with keyboard
- verify expanded/collapsed state updates correctly without layout glitches

5. Existing behavior non-regression
- offer section still renders correctly
- shared competencies section unchanged
- existing loading and error states unchanged

6. Privacy/copy check
- verify labels consistently indicate application-time sharing
- verify no decision-making wording introduced

## Acceptance Criteria for Step 10

Step 10 is complete when:

1. recruiter applicants page shows a matching snapshot section per applicant
2. matching data is clearly labeled as shared at application time
3. payload is rendered using reusable `JsonPayloadViewer` from Step 9 inside a collapsible section (collapsed by default)
4. null snapshot rows render a clear fallback without UI errors
5. existing applicant list behavior and consent boundaries remain intact
6. UI copy remains decision-supporting and transparency-focused

## Assumptions and Defaults

- backend recruiter applicants response contract remains stable for this step
- `shared_matching.result_payload` remains a JSON object suitable for direct rendering
- this step is frontend-only and intentionally avoids explanation templating logic
- deterministic score meaning comes from backend payload and is not reinterpreted by frontend
