# Phase 4 Plan: Recruiter UI Frontend Explanation Rollout (Detailed)

## Summary

This document defines the frontend implementation pass for Phase 4 explanation UX on the recruiter side.

Goal:

- render consent-shared matching explanation in a structured format for recruiter applicants view
- reuse seeker-side explanation UI primitives to keep behavior consistent and implementation small
- keep raw snapshot payload available in a collapsed disclosure for transparency and auditability

This plan does **not** change matching logic, score calculation, privacy boundaries, or consent flow.

---

## Locked Product Decisions

These decisions are fixed for this implementation pass:

1. Scope: implement recruiter applicants screen integration only (no broad recruiter page redesign).
2. Reuse-first: use existing `MatchingExplanationPanel.vue` from seeker rollout.
3. Recruiter visibility: hide development roadmap (`showRoadmap = false`) even if payload includes roadmap data.
4. Transparency: raw snapshot payload remains available via `<details>` collapsed by default.
5. Fallback behavior: when `shared_matching` exists but `explanation` is null, show a clear structured-explanation-unavailable note and keep raw payload visible.

---

## Current Baseline

Current behavior in recruiter applicants view (`/recruiter/job-offers/{id}/applicants`):

- recruiter sees application-time shared profile snapshot and shared competency list
- shared matching metadata is shown (score, algorithm version, snapshot timestamp)
- matching snapshot is primarily exposed as raw JSON payload in disclosure block
- no structured explanation rendering is currently shown

Current frontend/backend readiness:

- frontend has explanation types in `frontend/src/types/domain.ts`
- reusable structured renderer exists in `frontend/src/components/MatchingExplanationPanel.vue`
- seeker detail view already integrates this component and explanation label hydration
- recruiter API response type supports `shared_matching.explanation?: MatchingExplanation | null`

Gap:

- recruiter applicants view still needs structured explanation integration and explanation-key label hydration.

---

## In Scope

- Recruiter applicants view integration of structured explanation panel.
- Reuse of seeker-built component and disclosure interaction patterns.
- Label hydration expansion to include explanation competency keys.
- Null-safe recruiter fallback states for legacy/malformed explanation payloads.
- Manual validation and build/type-check validation.

## Out of Scope

- Any backend API changes.
- Changes to scoring formulas or explanation generation templates.
- Seeker page modifications.
- Recruiter information architecture redesign beyond explanation insertion.
- i18n/localization.

---

## Reusable Components and Patterns from Seeker UI

The recruiter rollout should intentionally reuse the following existing pieces:

1. `frontend/src/components/MatchingExplanationPanel.vue`
   - already implements summary, strengths, gaps, optional roadmap, transparency notes
   - already accepts `showRoadmap` flag suitable for recruiter-safe rendering

2. `frontend/src/components/JsonPayloadViewer.vue`
   - existing raw JSON transparency block in recruiter view remains the canonical disclosure payload renderer

3. `matching-disclosure` UI pattern in `frontend/src/styles.css`
   - same collapsed disclosure behavior and open/closed label toggling as seeker screen

4. Catalog label cache integration (`useCatalogLabelCache`)
   - same competency label resolution strategy with graceful fallback when labels are unavailable

5. Competency key collection pattern from seeker view
   - recruiter view should collect explanation keys (highlights/gaps) similarly for label hydration

---

## Target Recruiter UX

In each applicant card under **Shared matching result**:

1. Show shared snapshot metadata (score, algorithm version, snapshot timestamp) as today.
2. If `shared_matching.explanation` exists:
   - render `MatchingExplanationPanel`
   - show summary, strengths, gaps, transparency notes
   - hide development roadmap
3. If `shared_matching.explanation` is null but `shared_matching` exists:
   - show short fallback note indicating structured explanation is unavailable for this snapshot
   - still show raw payload disclosure
4. Always keep raw snapshot payload available through collapsed disclosure.
5. If `shared_matching` is null:
   - keep existing no-snapshot message unchanged.

UX copy constraints:

- maintain decision-support framing
- maintain consent/snapshot wording
- avoid decision-making language (accepted/rejected/system decision implications)

---

## View Integration Plan

Update `frontend/src/views/recruiter/RecruiterJobOfferApplicantsView.vue`.

### Template changes

In applicant `shared_matching` block:

1. Keep existing metadata summary grid.
2. Insert structured explanation render path:
   - `v-if="applicant.shared_matching.explanation"` render `MatchingExplanationPanel`
   - pass `:show-roadmap="false"`
   - pass recruiter-specific summary title (for example: `"Shared match explanation"`)
3. Add fallback path:
   - `v-else` under `shared_matching` template
   - show section note: structured explanation unavailable for this snapshot
4. Keep existing raw payload `<details class="matching-disclosure">` block after structured/fallback content.
5. Keep outer `v-else` behavior for missing `shared_matching` unchanged.

### Script changes

1. Import `MatchingExplanationPanel`.
2. Add helper to collect explanation competency keys from loaded applicants:
   - include `shared_matching.explanation.highlights[*].competency_key`
   - include `shared_matching.explanation.gaps[*].competency_key`
   - ignore roadmap keys for recruiter rendering (roadmap hidden)
   - skip null-safe when explanation missing
3. Update `loadApplicants()` hydration step:
   - keep existing shared profile competency key hydration
   - merge with explanation keys
   - deduplicate via `Set`
   - call `labelCache.hydrateKeys(uniqueKeys)` in fire-and-forget mode

### Guardrails

- Do not change route behavior or params handling.
- Do not change recruiter access scope or application visibility rules.
- Do not attempt client-side explanation synthesis from `result_payload`.

---

## Styling Plan

Primary expectation: existing seeker-introduced explanation styles are sufficient.

Use existing classes:

- `.explanation-panel`
- `.explanation-summary-card`
- `.explanation-table`
- `.explanation-list`
- `.competency-cell-main`
- `.competency-cell-key`
- `.matching-disclosure`

Optional minimal additions only if needed after manual QA:

- recruiter-card spacing adjustment around explanation panel
- minor typography alignment within applicant cards

Do not introduce a new visual system for this pass.

---

## Implementation Sequence

1. Update recruiter applicants view template with explanation panel + fallback state.
2. Update recruiter applicants view script imports and explanation-key hydration helper.
3. Verify no type changes are required beyond existing contracts.
4. Run `npm run type-check`.
5. Run `npm run build`.
6. Execute manual QA scenarios listed below.

---

## Manual QA Scenarios

1. Applicant with full structured explanation:
   - summary/strengths/gaps/transparency notes render
   - roadmap is not shown
2. Applicant with explanation gaps only:
   - strengths empty-state text is shown
   - gaps render with level context and details
3. Applicant with `shared_matching.explanation = null`:
   - metadata remains visible
   - fallback note is visible
   - raw payload disclosure still works
4. Applicant with `shared_matching = null`:
   - existing no-snapshot message remains
5. Label cache miss/error:
   - competency key fallback renders; UI does not show blank labels
6. Raw payload disclosure behavior:
   - collapsed by default
   - show/hide labels toggle correctly
7. Regression checks:
   - no change in consent/snapshot copy semantics
   - no change in applicant list visibility logic

---

## Acceptance Criteria

Recruiter frontend explanation rollout is complete when:

1. recruiter applicants UI shows structured explanation for rows where `shared_matching.explanation` is present
2. recruiter explanation view excludes development roadmap
3. raw snapshot payload remains available via collapsible disclosure
4. `shared_matching.explanation = null` rows render graceful fallback message without page errors
5. `shared_matching = null` rows remain supported
6. competency labels are hydrated for shared profile and explanation competency keys
7. `npm run type-check` and `npm run build` pass

---

## Assumptions and Defaults

- language remains English-only
- explanation text is backend-authored and treated as canonical
- recruiter UI is a minimal integration pass; no redesign in this phase
- existing shared styles from seeker rollout are reused as baseline
- matching logic, algorithm behavior, and privacy boundaries remain unchanged
