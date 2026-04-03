# Phase 4 Plan: Seeker UI Frontend Explanation Rollout (Detailed)

## Summary

This document defines the frontend implementation pass for Phase 4 explanation UX on the seeker side.

Goal:

- replace raw JSON as the **primary** seeker analysis UI with structured explanation rendering
- keep raw payload available for transparency in a collapsed disclosure
- introduce reusable explanation UI primitives so recruiter structured explanation rollout becomes a small follow-up

This plan does **not** change matching logic, score calculation, privacy boundaries, or consent flow.

---

## Locked Product Decisions

These decisions are fixed for this implementation pass:

1. Scope: implement seeker screen now and build shared explanation UI base components.
2. Competency display: use catalog label cache when available; fall back to competency key.
3. Text source: use backend explanation text as canonical content; frontend only adds layout and labels.
4. Transparency: raw payload remains available in `<details>` collapsed by default.
5. Behavior: no changes to analysis trigger flow (`Run private analysis` button behavior remains).

---

## Current Baseline

Current behavior in seeker offer detail:

- seeker can run private analysis from `/seeker/job-offers/{id}`
- analysis result is shown only as raw JSON payload
- consent/apply section and privacy copy already exist and must remain intact

Current backend readiness:

- API already returns `explanation` with private analysis payload
- recruiter shared matching payload already includes optional `explanation`

Gap:

- frontend types and rendering are not yet aligned with Phase 4 explanation contract

---

## In Scope

- TypeScript domain type updates for explanation payload.
- New reusable explanation rendering component(s) in `frontend/src/components`.
- Seeker detail view integration to render structured explanation.
- Label hydration and fallback behavior for explanation competency keys.
- CSS additions for explanation cards/sections/tables/lists.
- Manual validation and build/type-check validation.

## Out of Scope

- Recruiter page migration in this pass (component base will support it).
- Any backend API changes.
- New charts or analytics visuals.
- i18n/localization.
- Changes to scoring formulas or scoring constants.

---

## Target Seeker UX

In the **Private analysis** section:

1. User clicks `Run private analysis`.
2. On success, UI renders structured explanation blocks:
   - summary card (headline, status, notices)
   - strengths list/table
   - gaps list/table
   - development roadmap table
   - transparency notes
3. Raw payload remains available via `Show raw analysis payload` disclosure.
4. If analysis has not been run yet, existing empty-state guidance stays visible.
5. Error behavior remains unchanged (`ApiErrorNotice` continues to show API errors).

---

## Data Contract Changes (Frontend)

Update `frontend/src/types/domain.ts` with explicit explanation models aligned to backend schema.

### Add unions

- `ExplanationAudience = "seeker" | "recruiter"`
- `ExplanationHighlightKind = "strength"`
- `ExplanationGapKind = "missing" | "insufficient"`

### Add interfaces

- `ExplanationSummary`
- `ExplanationHighlightItem`
- `ExplanationGapItem`
- `ExplanationRoadmapItem`
- `MatchingExplanation`

### Extend existing response types

- `PrivateMatchingAnalysisResponse` gains `explanation: MatchingExplanation`
- `RecruiterApplicantSharedMatching` gains `explanation?: MatchingExplanation | null`

Rationale:

- mirrors backend contract
- removes `any`/implicit-shape usage
- enables safe shared component consumption

---

## UI Component Design (Shared Base)

Create one reusable component:

- `frontend/src/components/MatchingExplanationPanel.vue`

### Component responsibility

- render explanation structure consistently
- support both audiences through props/flags
- remain pure presentation (no API calls, no business rules)

### Props contract

- `explanation: MatchingExplanation`
- `competencyLabel: (competencyKey: string) => string`
- `showRoadmap?: boolean` (default `true`)
- `summaryTitle?: string` (default `Explanation summary`)

### Rendering rules

1. Summary card:
   - `headline`
   - `status_label`
   - optional `must_have_notice`
   - optional `no_requirements_notice`
   - `decision_support_notice`
2. Strengths:
   - empty-state text when list is empty
   - each row shows competency label/key, priority, and backend text
3. Gaps:
   - empty-state text when list is empty
   - each row shows competency label/key, kind, priority, optional expected/current levels, backend text
4. Development roadmap:
   - render only when `showRoadmap === true` and `explanation.development_roadmap !== null`
   - empty-state text if roadmap list is empty
5. Transparency notes:
   - render as bullet list
   - always present

### Key display format

For strengths/gaps/roadmap competency field:

- primary text: `competencyLabel(key)`
- secondary muted text: raw `key`

This keeps readability while preserving audit traceability.

---

## Seeker View Integration

Update `frontend/src/views/seeker/SeekerJobOfferDetailView.vue`.

### Template changes

- In `Private analysis` section:
  - keep run button and existing loading/error behavior
  - replace primary `JsonPayloadViewer` with:
    - structured explanation block (`MatchingExplanationPanel`) when `analysisResult` exists
    - empty-state message when null
  - add `<details class="matching-disclosure">` for raw payload:
    - summary text toggles between show/hide labels
    - `JsonPayloadViewer` inside details
    - collapsed by default

### Script changes

- Import `MatchingExplanationPanel`.
- Keep `analysisResult` state and `runPrivateAnalysis` logic as-is.
- Add helper to gather explanation keys for label hydration.
- After successful analysis fetch:
  - assign result to `analysisResult`
  - collect keys from:
    - `explanation.highlights[*].competency_key`
    - `explanation.gaps[*].competency_key`
    - `explanation.development_roadmap[*].competency_key` (if list)
  - call `labelCache.hydrateKeys(uniqueKeys)` in fire-and-forget mode

### Guardrails

- Do not alter apply/withdraw behavior.
- Do not alter offer loading logic.
- Do not alter existing privacy copy semantics.

---

## Styling Plan

Update `frontend/src/styles.css` with explanation-focused classes:

- `.explanation-panel`
- `.explanation-summary-card`
- `.explanation-notice`
- `.explanation-list`
- `.explanation-table`
- `.competency-cell-main`
- `.competency-cell-key`

Styling goals:

- keep visual consistency with existing panel/table styles
- emphasize readability of explanation text
- preserve responsive behavior on mobile widths
- avoid overflow for normal text content

Mobile rules:

- stack summary grid into one column
- keep explanation tables legible (`font-size` adjustment only if needed)
- maintain horizontal scroll only for raw JSON block

---

## Implementation Sequence

1. Update domain types in `frontend/src/types/domain.ts`.
2. Implement `MatchingExplanationPanel.vue`.
3. Integrate panel into seeker detail view and retain raw disclosure block.
4. Add/adjust CSS rules for explanation layout.
5. Run `npm run type-check`.
6. Run `npm run build`.
7. Perform manual QA scenarios listed below.

---

## Manual QA Scenarios

1. No analysis run:
   - seeker sees empty guidance, no structured explanation block, no errors.
2. Typical analysis with matches and gaps:
   - summary/strengths/gaps/roadmap/notes all render.
3. Must-have gap case:
   - must-have notice is visible in summary.
4. No-requirements case:
   - no-requirements notice visible; strengths/gaps/roadmap empty-state messages render correctly.
5. Unknown algorithm fallback:
   - explanation renders generic fallback safely; page does not crash.
6. Label cache miss:
   - key fallback is shown; no blank competency labels.
7. Raw payload disclosure:
   - collapsed by default, expands/collapses correctly.

---

## Acceptance Criteria

Implementation is complete when all are true:

1. Seeker analysis UI shows structured explanation as primary content.
2. Raw analysis payload remains accessible through collapsed disclosure.
3. Frontend types explicitly model explanation payload and compile cleanly.
4. Label rendering uses cache-first with key fallback across explanation sections.
5. `npm run type-check` passes.
6. `npm run build` passes.
7. Existing apply/withdraw consent flow behavior remains unchanged.

---

## Risks and Mitigations

1. Risk: backend explanation shape drift causes runtime rendering failures.
   - Mitigation: strict TS interfaces and null-safe rendering guards.
2. Risk: missing label hydration makes explanation hard to read.
   - Mitigation: hydrate explanation keys immediately after analysis fetch and always show key fallback.
3. Risk: structured UI could accidentally imply automated decision-making.
   - Mitigation: preserve backend decision-support notice prominently in summary.

---

## Follow-Up (Not in This Pass)

After this seeker rollout is merged:

1. Reuse `MatchingExplanationPanel.vue` in recruiter applicants view.
2. Pass `showRoadmap=false` for recruiter audience.
3. Keep existing recruiter snapshot/raw payload disclosure behavior intact.
