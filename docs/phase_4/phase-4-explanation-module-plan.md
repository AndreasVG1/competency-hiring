# Phase 4 Plan: Explanation Module (Role-Aware, Backend-First)

## Summary

Phase 4 introduces a dedicated explanation module that transforms deterministic matching payloads into structured, human-readable feedback for each audience:

- **Job seeker**: receives transparent score interpretation, strengths, gaps, and a prioritized development roadmap.
- **Recruiter**: receives transparent score interpretation, strengths, and gaps for consent-shared applications, but **no development roadmap**.

This phase keeps matching logic unchanged and uses explanation as a presentation layer over existing scoring facts.

The plan follows `AGENTS.md` constraints:

- transparency over complexity
- privacy and explicit consent boundaries
- exact-match deterministic MVP logic
- modular monolith boundaries with thin route handlers
- decision-supporting language only (no automated hiring decisions)

## Why Phase 4 Exists

Phase 3 intentionally surfaced matching as raw JSON in frontend screens to maximize transparency quickly. That was a useful intermediate step, but now users need a clearer explanation layer that:

- improves readability without hiding underlying facts
- keeps explanation deterministic and auditable
- supports role-specific output rules
- preserves raw payload access for traceability

## Scope and Non-Goals

### In scope

- new backend module `backend/app/modules/explanation`
- deterministic explanation generation from matching payload
- role-aware explanation output (`seeker`, `recruiter`)
- API response extension to include both raw payload and explanation
- frontend structured cards/tables for explanation display
- raw JSON retained in collapsible UI section
- tests for explanation behavior and privacy-safe visibility
- Phase 4 documentation and acceptance checklist

### Out of scope

- changes to matching formula, weights, or scoring constants
- charts and visual analytics
- explanation persistence in database
- multilingual/i18n explanation templates
- semantic inference, embeddings, similarity ranking, or any black-box layer
- recruiter access to seeker-private analysis without application consent

## Current Baseline from Phase 3

Already implemented and must remain intact:

- deterministic exact-match engine in `modules/matching`
- private seeker analysis endpoint
- application-time shared matching snapshot persistence
- recruiter visibility only for applied candidates on owned offers
- raw payload rendering in seeker and recruiter UIs

Phase 4 builds **on top** of this baseline and must not weaken consent/visibility rules.

## Architecture and Module Boundaries

### New backend module

Create:

- `backend/app/modules/explanation/__init__.py`
- `backend/app/modules/explanation/schemas.py`
- `backend/app/modules/explanation/service.py`
- `backend/app/modules/explanation/templates.py`

Responsibilities:

- convert matching payload facts into structured explanation blocks
- enforce deterministic ordering and deterministic text templates
- apply audience filtering (for example recruiter roadmap exclusion)
- provide version-aware renderers by `algorithm_version`

Non-responsibilities:

- no scoring calculations
- no DB persistence
- no authorization checks

### Existing module integration

- `modules/matching` remains source of scoring truth.
- `modules/seeker` and `modules/applications` orchestrate explanation generation on read.
- Route handlers remain thin and return typed responses.

## Explanation Contract (Normative for Phase 4)

Explanation is added as a structured field while preserving existing payload.

### Audience enum

- `seeker`
- `recruiter`

### Top-level explanation object

```json
{
  "audience": "seeker",
  "algorithm_version": "v2_exact_priority_level_dual_signal",
  "summary": {
    "headline": "Your current suitability score is 72.5/100.",
    "status_label": "Must-have gaps require attention.",
    "decision_support_notice": "This analysis supports your decision and does not make hiring decisions.",
    "must_have_notice": "At least one must-have competency is currently missing.",
    "no_requirements_notice": null
  },
  "highlights": [
    {
      "kind": "strength",
      "competency_key": "comp_python",
      "priority": "important",
      "text": "Meets expected level for Python (important)."
    }
  ],
  "gaps": [
    {
      "kind": "missing",
      "competency_key": "comp_testing",
      "priority": "must_have",
      "text": "Missing must-have competency: Testing.",
      "reason_code": "missing_competency"
    },
    {
      "kind": "insufficient",
      "competency_key": "comp_sql",
      "priority": "must_have",
      "expected_level": "intermediate",
      "current_level": "beginner",
      "text": "SQL is below expected level (beginner vs expected intermediate).",
      "reason_code": "level_below_expected"
    }
  ],
  "development_roadmap": [
    {
      "competency_key": "comp_sql",
      "priority": "must_have",
      "target_level": "intermediate",
      "estimated_point_gain": 2.5,
      "text": "Improving SQL to intermediate would recover about 2.5 points."
    }
  ],
  "transparency_notes": [
    "Exact competency key matching only.",
    "Priority weights and expected levels are deterministic.",
    "No semantic inference or hidden scoring is used."
  ]
}
```

### Role-specific rule

- seeker explanation includes `development_roadmap` (possibly empty list).
- recruiter explanation sets `development_roadmap` to `null`.

### No-requirements rule

When status is `not_applicable_no_requirements`:

- include explicit summary note that recruiter defined no requirements
- return empty `highlights`, `gaps`, and `development_roadmap` (`[]` for seeker, `null` recruiter)
- transparency notes still present

### Determinism rules

- explanation lists use matching payload’s stable ordering principles:
  1. `must_have`, `important`, `nice_to_have`
  2. point loss descending (when applicable)
  3. competency key ascending
- template selection depends only on payload facts and audience
- no random phrases or time-dependent wording

## API and Type Changes

### Seeker private analysis endpoint

Endpoint (unchanged path):

- `GET /api/v1/seeker/job-offers/{job_offer_id}/analysis`

Response change:

- keep current matching payload fields unchanged
- add `explanation` object

Recommended backend schema evolution:

- extend `MatchingResultPayload` with optional `explanation` for response use, **or**
- define a new response model `PrivateMatchingAnalysisWithExplanationResponse` containing:
  - all existing matching fields
  - `explanation`

Preferred choice for clarity: introduce new response model to avoid coupling pure matcher schema to presentation layer.

### Recruiter applicants endpoint

Endpoint (unchanged path):

- `GET /recruiter/job-offers/{job_offer_id}/applicants`

Response change (inside each applicant):

- keep `shared_matching.result_payload`
- keep `shared_matching.algorithm_version`, `score`, `snapshot_created_at`
- add `shared_matching.explanation` generated from snapshot payload on read

### Version handling policy

- if `algorithm_version` is known (`v2_exact_priority_level_dual_signal`), use full renderer
- if unknown, return fallback explanation with:
  - generic summary
  - transparency note that detailed template is unavailable for that version
  - empty structured lists
  - raw payload still available to client

No endpoint should fail solely because explanation renderer is unknown.

## Backend Implementation Plan

### [X] Milestone 4A: Explanation module foundation

1. Create explanation schemas and template constants.
2. Add pure service function:
   - input: matching payload + audience
   - output: typed explanation object
3. Add renderer registry keyed by `algorithm_version`.
4. Implement fallback renderer for unknown versions.

### [X] Milestone 4B: Seeker integration

1. In seeker analysis service flow, generate explanation from private matching payload.
2. Return combined response (matching + explanation).
3. Keep existing access checks and published-offer validation unchanged.

### [ ] Milestone 4C: Recruiter integration

1. In recruiter applicants read flow, generate explanation from each `shared_matching.result_payload`.
2. Use `audience = recruiter`.
3. Attach explanation to `shared_matching` object only when snapshot exists.
4. Preserve null-safe behavior for legacy rows with no matching snapshot.

### [ ] Milestone 4D: Robustness and docs

1. Add explanation-focused unit and API tests.
2. Add Phase 4 implementation note.
3. Record acceptance checklist and known limitations.

## Frontend Implementation Plan

### Seeker UI (`/seeker/job-offers/{id}`)

Replace raw JSON as primary content with structured explanation cards/tables:

- Summary card:
  - score
  - status label
  - must-have warning / no-requirements note
  - decision-support notice
- Strengths section (matched items)
- Gaps section:
  - missing and insufficient entries
  - priority + level context
- Development roadmap table:
  - competency
  - target level
  - estimated point gain
- Transparency notes section
- Keep raw payload view in collapsible `<details>` (collapsed by default)

### Recruiter UI (`/recruiter/job-offers/{id}/applicants`)

For each applicant shared matching section:

- show structured explanation blocks:
  - summary
  - strengths
  - gaps
  - transparency notes
- do **not** show development roadmap
- keep raw snapshot payload in collapsible section
- keep explicit copy: “shared at application time”

### Frontend type updates

- add explanation domain types and unions in `frontend/src/types/domain.ts`
- extend seeker analysis response type with `explanation`
- extend recruiter `shared_matching` type with `explanation`

### UX copy rules

All explanation text and labels must remain:

- decision-supporting
- privacy-aware
- non-judgmental and non-automated

Avoid wording like “accepted”, “rejected”, “system decision”, or candidate ranking implication.

## Testing Strategy

### Backend unit tests (highest priority)

Add `backend/tests/test_explanation_service.py` with cases:

- full match explanation
- mixed missing + insufficient explanation
- must-have missing warning logic
- no requirements explanation behavior
- role-specific output difference (roadmap shown/hidden)
- deterministic ordering and stable phrase selection
- unknown algorithm fallback

### Backend integration/API tests

Update/add tests in seeker/recruiter test suites:

- seeker analysis response includes `explanation`
- recruiter applicants response includes `shared_matching.explanation`
- recruiter response excludes roadmap fields
- unknown version snapshot still returns response with fallback explanation
- existing privacy/authorization boundaries remain unchanged

### Regression tests

- matching score values and breakdown behavior unchanged
- apply snapshot immutability unchanged
- legacy applicants with null `shared_matching` remain supported

### Frontend verification

From `frontend/`:

- `npm run type-check`
- `npm run build`

Manual scenarios:

1. Seeker runs private analysis and sees structured explanation.
2. Seeker sees roadmap and transparency notes.
3. Recruiter sees shared explanation without roadmap.
4. Raw JSON payload still accessible via disclosure.
5. Null `shared_matching` rows still render graceful fallback.

## Acceptance Criteria

Phase 4 is complete when:

1. backend explanation module exists and is independently unit-tested
2. seeker analysis API returns both matching payload and explanation
3. recruiter applicants API returns consent-scoped explanation from snapshot payload
4. recruiter explanation excludes development roadmap by design
5. seeker and recruiter UIs present structured explanation cards/tables (no charts)
6. raw payload remains visible via collapsible section for transparency
7. matching formula and privacy boundaries remain unchanged
8. unknown algorithm versions return safe fallback explanation instead of failing

## Assumptions and Defaults

- language is English only in Phase 4
- explanation generation is on-read only and not persisted
- matching payload remains canonical source for explanation facts
- explanation templates are deterministic and version-aware
- competency labels continue to be resolved by existing frontend catalog label cache

## Known Limitations (Explicit)

- explanation text is template-based and currently not localized
- fallback for unknown algorithm versions is intentionally minimal
- explanation quality depends on completeness of matching payload fields

## Future Extension Path (Post-Phase 4, Optional)

- i18n template packs without changing scoring logic
- richer explanation metadata (for example confidence markers tied to explicit rule coverage)
- optional persisted explanation snapshots if audit requirements expand
- UI personalization preferences (compact vs detailed explanation view)
