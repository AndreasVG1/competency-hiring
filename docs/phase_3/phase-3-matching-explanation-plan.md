# Phase 3 Plan: Private Matching + Explainable Results

## Summary

Build Phase 3 so that:
- a job seeker can run a private, deterministic suitability analysis for a published offer
- the backend returns an explainable score breakdown based on exact competency matching
- missing and insufficient competencies are clearly identified
- recruiter-visible matching results appear only after explicit consent via apply
- recruiter views read the application-time matching snapshot, not mutable live data

This plan follows `AGENTS.md` product and architecture rules:
- transparency over complexity
- privacy and user control
- exact-match MVP logic
- deterministic and testable business logic
- modular monolith with thin route handlers

## Scope and Non-Goals

### In scope
- exact `competency_key` matching only
- deterministic score calculation from requirement priority and seeker level
- private seeker analysis endpoint(s)
- explanation-ready payload from matching module
- consent-time snapshot of shared matching result
- recruiter access to matching result only for owned offers and applied candidates

### Out of scope
- related-competency inference
- semantic similarity, embeddings, or vector search
- black-box ranking or automated screening
- recruiter browsing of seeker private analyses
- live runtime dependency on external data sources

## Fixed MVP Matching Specification (Option 1)

This section is normative for Phase 3 implementation.

### Inputs
- job offer requirements from SQLite:
  - `competency_key`
  - `priority` (`must_have`, `important`, `nice_to_have`)
- seeker competencies from SQLite:
  - `competency_key`
  - `level` (`beginner`, `intermediate`, `advanced`)

### Mappings

Priority weight mapping:
- `must_have` -> `5`
- `important` -> `3`
- `nice_to_have` -> `1`

Level numeric mapping:
- `beginner` -> `1`
- `intermediate` -> `2`
- `advanced` -> `3`

Minimum expected level by priority (global rule):
- `must_have` -> `intermediate` (`2`)
- `important` -> `intermediate` (`2`)
- `nice_to_have` -> `beginner` (`1`)

### Per-requirement evaluation
For each job requirement:
1. Lookup seeker competency by exact `competency_key`.
2. If missing:
- `status = "missing"`
- `earned_points = 0`
- `max_points = priority_weight`
3. If present:
- `ratio = min(seeker_level_numeric / expected_level_numeric, 1.0)`
- `earned_points = priority_weight * ratio`
- `status = "matched"` when `seeker_level_numeric >= expected_level_numeric`
- `status = "insufficient"` when `seeker_level_numeric < expected_level_numeric`

### Overall score
- `total_max_points = sum(max_points)`
- `total_earned_points = sum(earned_points)`
- `score = round(100 * total_earned_points / total_max_points, 1)` when `total_max_points > 0`
- fallback when no requirements:
  - `score = 0.0`
  - `status = "not_applicable_no_requirements"`
  - explanation should explicitly state that no requirements were defined

### Dual-signal status and must-have coverage (v2)
- no additional score penalty is applied for missing `must_have` competencies
- compute `must_have_coverage` from requirements with priority `must_have`:
  - `total_count`
  - `matched_count`
  - `insufficient_count`
  - `missing_count`
  - `coverage_ratio = matched_count / total_count` (or `0.0` when `total_count == 0`)
- `critical_gap_present = true` when `must_have_coverage.missing_count > 0`
- status policy:
  - `not_applicable_no_requirements` when no requirements
  - `ok_with_must_have_gaps` when `critical_gap_present = true`
  - `ok` otherwise

### Determinism rules
- no randomness
- no time-dependent scoring inputs
- stable ordering of lists by:
  1. priority severity (`must_have`, `important`, `nice_to_have`)
  2. point loss descending
  3. `competency_key` ascending as tiebreaker

## Explainability Output Contract

The matching module returns structured data for direct UI usage and explanation text generation.

Suggested response shape:

```json
{
  "algorithm_version": "v2_exact_priority_level_dual_signal",
  "scope": "private_preview",
  "job_offer_id": 101,
  "seeker_user_id": 17,
  "score": 72.5,
  "status": "ok_with_must_have_gaps",
  "critical_gap_present": true,
  "must_have_coverage": {
    "total_count": 2,
    "matched_count": 0,
    "insufficient_count": 1,
    "missing_count": 1,
    "coverage_ratio": 0.0
  },
  "totals": {
    "earned_points": 14.5,
    "max_points": 20.0,
    "requirements_count": 6,
    "matched_count": 3,
    "insufficient_count": 2,
    "missing_count": 1
  },
  "weights_used": {
    "priority_weights": {
      "must_have": 5,
      "important": 3,
      "nice_to_have": 1
    },
    "expected_level_by_priority": {
      "must_have": "intermediate",
      "important": "intermediate",
      "nice_to_have": "beginner"
    }
  },
  "breakdown": [
    {
      "competency_key": "comp_sql",
      "priority": "must_have",
      "expected_level": "intermediate",
      "seeker_level": "beginner",
      "status": "insufficient",
      "earned_points": 2.5,
      "max_points": 5.0,
      "point_loss": 2.5,
      "reason_code": "level_below_expected"
    }
  ],
  "missing_competencies": [
    {
      "competency_key": "comp_testing",
      "priority": "important",
      "reason_code": "missing_competency"
    }
  ],
  "insufficient_competencies": [
    {
      "competency_key": "comp_sql",
      "priority": "must_have",
      "expected_level": "intermediate",
      "seeker_level": "beginner",
      "reason_code": "level_below_expected"
    }
  ],
  "development_targets": [
    {
      "competency_key": "comp_sql",
      "priority": "must_have",
      "suggested_target_level": "intermediate",
      "point_gain_if_reached": 2.5
    }
  ]
}
```

## Milestone Breakdown

### Milestone 3A: Private Matching Engine + Seeker Preview
Goal:
- implement deterministic exact-match engine and private analysis endpoint for seekers

### Milestone 3B: Explanation Payload + Seeker UI Integration
Goal:
- expose transparent breakdown in seeker UI with clear matched/missing/insufficient sections

### Milestone 3C: Consent-Time Matching Snapshot + Recruiter Visibility
Goal:
- compute and store shareable matching result at application time and show it to recruiter only after consent

## Step-by-Step Tasks

1. [X] Create Phase 3 implementation note and boundaries
- Add/update `docs/phase_3` note that states exact-match-only scope.
- Record that semantic/graph inference remains out of scope for official Phase 3 MVP.

2. [X] Add matching module skeleton under backend modular monolith
- Create `backend/app/modules/matching/`.
- Add `engine.py` (pure calculation), `service.py` (data orchestration), `schemas.py`.
- Keep route handlers thin by delegating to matching service.

3. [X] Implement pure deterministic matching engine
- Input: normalized requirement and seeker competency arrays.
- Output: score + explainability payload.
- Enforce stable ordering and deterministic rounding.

4. [X] Add strict validation and edge-case handling
- Empty requirement set behavior.
- Duplicate guard assumptions (already constrained in DB) and safe fallback.
- Unknown enum value defense with explicit errors.

5. [X] Add seeker private analysis endpoint(s)
- Recommended endpoint: `GET /seeker/job-offers/{id}/analysis`.
- Enforce seeker role and published-offer-only visibility.
- Return private analysis only to current seeker.

6. [X] Add shared matching snapshot persistence model
- Add new SQLite table for application-time matching snapshot:
  - `application_id` (PK/FK to `applications`)
  - `algorithm_version`
  - `score`
  - `result_payload` (JSON)
  - `created_at`
- Keep snapshot immutable once created.

7. [X] Integrate matching into apply flow
- During `apply_to_published_job_offer`, compute matching from application-time seeker data and current offer requirements.
- Persist matching snapshot in same transaction as application + profile snapshot.
- Ensure rollback safety on failure.

8. [ ] Extend recruiter applicant read model
- Include shared matching snapshot fields in recruiter applicant responses.
- Keep ownership checks unchanged and mandatory.
- Never expose private pre-apply analyses.

9. [ ] Add seeker UI analysis section in offer detail page
- In `/seeker/job-offers/{id}`, add “Run private analysis” section.
- Display score and breakdown with explicit explanation labels.
- Keep language decision-supporting, not decision-making.

10. [ ] Add recruiter UI section for application-time matching
- In `/recruiter/job-offers/{id}/applicants`, show snapshot matching result per applicant.
- Label clearly as “shared at application time”.

11. [ ] Keep explanation logic centralized
- For now, explanation payload is produced directly by matching service output contract.
- If a separate explanation module is later introduced, it should consume this structured payload without changing core scoring.

12. [ ] Add unit tests for matching engine (highest priority)
- happy path full match
- missing competency handling
- insufficient level handling
- mixed priorities and weighted score correctness
- no requirements edge case
- deterministic ordering and rounding checks

13. [ ] Add service/API tests for access and privacy
- seeker can access own private analysis
- recruiter cannot access seeker private analysis endpoint
- analysis only for published offers
- structured error responses maintained

14. [ ] Add consent snapshot integrity tests
- seeker runs private analysis
- seeker applies
- seeker changes competencies afterwards
- recruiter still sees original application-time matching snapshot

15. [ ] Add integration tests around apply transaction behavior
- if snapshot write fails, application is not partially persisted
- duplicate apply still returns conflict

16. [ ] Finalize docs, acceptance checklist, and known limitations
- Document algorithm constants and versioning.
- Record known limitation: global expected-level rule by priority.
- Record future extensibility path without breaking v1 contract.

## Proposed API and Types

Base API route prefix:
- `/api/v1/`

Recommended backend routes:
- `GET /seeker/job-offers/{job_offer_id}/analysis`
- Existing route extended with snapshot generation side-effect:
  - `POST /seeker/job-offers/{job_offer_id}/apply`
- Existing recruiter route extended with shared matching data:
  - `GET /recruiter/job-offers/{job_offer_id}/applicants`

Recommended new response type additions:
- `MatchingAnalysisResponse`
- `MatchingBreakdownItem`
- `DevelopmentTargetItem`
- `RecruiterApplicantListItem.shared_matching` (snapshot result)

## Data Ownership and Privacy Rules for Phase 3

- SQLite remains the source of truth for all transactional matching outputs.
- Neo4j remains read-only catalog source for labels/keys, not runtime scorer dependency.
- Seeker private analysis is private by default and must never be exposed to recruiters.
- Recruiter sees matching result only after application consent, and from snapshot data.
- Snapshot matching data must be immutable and audit-friendly.

## Test Plan

- Scoring correctness:
- weighted formula returns expected score values
- exact-match-only behavior is enforced
- insufficient and missing classification is correct

- Privacy/authorization:
- only seekers can access seeker analysis endpoint
- recruiters cannot access private seeker analysis
- recruiter can see matching only for applicants on owned offers

- Consent/snapshot consistency:
- snapshot matching remains stable after seeker profile changes
- recruiter reads snapshot value, not recalculated live value

- API contracts:
- response structure is stable and typed
- structured validation and HTTP errors remain consistent

## Acceptance Criteria

Phase 3 is complete when:

1. seeker can run private analysis for published offers with deterministic score output
2. explanation-ready payload includes matched/missing/insufficient and development targets
3. apply flow stores application-time matching snapshot atomically
4. recruiter sees only consent-shared snapshot matching for owned offer applicants
5. tests cover score logic, privacy boundaries, and snapshot immutability
6. no semantic inference or black-box behavior is introduced

## Assumptions and Defaults

- Existing `RequirementPriority` and `CompetencyLevel` enums remain unchanged.
- Global expected-level mapping by priority is accepted for MVP simplicity.
- Overqualification does not provide bonus points above requirement max in v2.
- Missing must-have competencies do not apply a direct score penalty in v2; risk is surfaced through dual-signal fields.
- Private seeker analyses are computed on demand and are not persisted as history in v1/v2.
- Any future algorithm changes must increment `algorithm_version` and preserve backward compatibility for stored snapshots.
