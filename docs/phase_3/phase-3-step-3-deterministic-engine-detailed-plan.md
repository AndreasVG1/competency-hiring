# Phase 3 Step 3: Pure Deterministic Matching Engine (Detailed Plan)

## Goal

Implement Phase 3 step 3 by replacing the current stub in `backend/app/modules/matching/engine.py` with a fully deterministic, pure calculation engine that returns the explainability-ready `MatchingResultPayload`.

This step is intentionally scoped to engine logic and unit tests only.

## Why This Step Exists

Step 3 establishes the core scoring and explanation behavior required by Phase 3:

- exact `competency_key` matching
- deterministic weighted score calculation
- explicit classification of `matched`, `insufficient`, and `missing`
- structured output for UI explanation rendering

This aligns with `AGENTS.md` principles:

- transparency over complexity
- privacy and user control (no recruiter exposure handled here)
- exact-match MVP logic
- deterministic and testable business rules

## Scope Boundaries

### In scope for Step 3

- implement `calculate_exact_match_result(...)` in `engine.py`
- use fixed MVP mappings and formulas from `docs/phase_3/phase-3-matching-explanation-plan.md`
- produce complete `MatchingResultPayload` according to existing `schemas.py`
- enforce deterministic ordering rules across explanation lists
- add dedicated unit tests in backend test suite

### Out of scope for Step 3

- step 4 hardening work (unknown enum defense, duplicate guards)
- seeker analysis API route wiring
- application-time snapshot persistence
- recruiter-visible shared matching integration
- frontend UI integration

## Current Baseline in Repository

- `backend/app/modules/matching/engine.py` exists but raises `NotImplementedError`.
- `backend/app/modules/matching/service.py` already gathers:
  - published offer requirements
  - seeker competencies
  - and calls `calculate_exact_match_result(...)`
- `backend/app/modules/matching/schemas.py` already defines payload types.
- there are currently no matching engine tests in `backend/tests`.

## Fixed Algorithm Contract (Normative)

### Static mappings

Priority weight mapping:

- `must_have -> 5`
- `important -> 3`
- `nice_to_have -> 1`

Level numeric mapping:

- `beginner -> 1`
- `intermediate -> 2`
- `advanced -> 3`

Expected level by priority:

- `must_have -> intermediate`
- `important -> intermediate`
- `nice_to_have -> beginner`

### Per-requirement evaluation

For each requirement:

1. Find seeker competency by exact `competency_key`.
2. Compute `max_points = priority_weight`.
3. If competency is missing:
   - `status = "missing"`
   - `earned_points = 0.0`
   - `point_loss = max_points`
   - `reason_code = "missing_competency"`
4. If competency exists:
   - `ratio = min(seeker_level_numeric / expected_level_numeric, 1.0)`
   - `earned_points = max_points * ratio`
   - `status = "matched"` when seeker level >= expected level
   - `status = "insufficient"` when seeker level < expected level
   - `reason_code = "meets_expected_level"` for matched
   - `reason_code = "level_below_expected"` for insufficient
   - `point_loss = max_points - earned_points`

### Totals and score

- `total_max_points = sum(max_points)`
- `total_earned_points = sum(earned_points)`
- `score = round(100 * total_earned_points / total_max_points, 1)` when `total_max_points > 0`
- if no requirements:
  - `score = 0.0`
  - `status = "not_applicable_no_requirements"`
  - totals are all zero except counts derived from empty inputs

### v2 Dual-signal extension

- score formula remains unchanged in v2
- v2 adds must-have risk signaling:
  - `must_have_coverage` with matched/insufficient/missing counts and coverage ratio
  - `critical_gap_present` (`true` when any `must_have` competency is missing)
- v2 status policy:
  - `not_applicable_no_requirements` when no requirements
  - `ok_with_must_have_gaps` when `critical_gap_present = true`
  - `ok` otherwise

### Deterministic ordering

All list outputs that represent requirement outcomes must be stable using this key order:

1. priority severity: `must_have`, then `important`, then `nice_to_have`
2. `point_loss` descending
3. `competency_key` ascending

## Algorithm Walkthrough (Worked Example)

This walkthrough demonstrates the exact deterministic behavior with concrete input and output values.

### Input

Job offer requirements:

1. `comp_api` with priority `must_have`
2. `comp_sql` with priority `important`
3. `comp_docs` with priority `nice_to_have`

Seeker competencies:

1. `comp_api` at level `intermediate`
2. `comp_sql` at level `beginner`
3. `comp_docs` is not present

### Step A: Resolve static values per requirement

From the fixed mappings:

- `must_have`: `max_points = 5`, expected level = `intermediate` (`2`)
- `important`: `max_points = 3`, expected level = `intermediate` (`2`)
- `nice_to_have`: `max_points = 1`, expected level = `beginner` (`1`)

### Step B: Evaluate each requirement

#### Requirement 1: `comp_api` (`must_have`)

- seeker has competency at `intermediate` (`2`)
- ratio = `min(2 / 2, 1.0) = 1.0`
- earned points = `5 * 1.0 = 5.0`
- status = `matched`
- reason = `meets_expected_level`
- point loss = `5.0 - 5.0 = 0.0`

#### Requirement 2: `comp_sql` (`important`)

- seeker has competency at `beginner` (`1`)
- ratio = `min(1 / 2, 1.0) = 0.5`
- earned points = `3 * 0.5 = 1.5`
- status = `insufficient`
- reason = `level_below_expected`
- point loss = `3.0 - 1.5 = 1.5`

#### Requirement 3: `comp_docs` (`nice_to_have`)

- seeker competency is missing
- earned points = `0.0`
- status = `missing`
- reason = `missing_competency`
- point loss = `1.0 - 0.0 = 1.0`

### Step C: Totals and score

- total earned points = `5.0 + 1.5 + 0.0 = 6.5`
- total max points = `5.0 + 3.0 + 1.0 = 9.0`
- score = `round(100 * 6.5 / 9.0, 1) = round(72.222..., 1) = 72.2`
- status = `ok` (because `total_max_points > 0`)

### Step D: Deterministic ordering of output lists

Sort key: `(priority rank, -point_loss, competency_key)`.

Sorted `breakdown` order for this example:

1. `comp_api` (`must_have`, loss `0.0`, matched)
2. `comp_sql` (`important`, loss `1.5`, insufficient)
3. `comp_docs` (`nice_to_have`, loss `1.0`, missing)

Derived lists:

- `missing_competencies`: `comp_docs`
- `insufficient_competencies`: `comp_sql`
- `development_targets`: `comp_sql`, `comp_docs`
  - `comp_sql` gain if reached = `1.5`
  - `comp_docs` gain if reached = `1.0`

### Step E: Final payload highlights

- `algorithm_version = "v2_exact_priority_level_dual_signal"`
- `scope = "private_preview"`
- `critical_gap_present = false` (no missing must-have in this walkthrough)
- `must_have_coverage`: total `1`, matched `1`, insufficient `0`, missing `0`, ratio `1.0`
- `totals`: matched `1`, insufficient `1`, missing `1`, requirements `3`
- explanation sections are consistent with one shared evaluated row set (no recomputation drift)

## Output Construction Requirements

The function returns `MatchingResultPayload` with:

- `algorithm_version = "v2_exact_priority_level_dual_signal"`
- `scope = "private_preview"`
- pass-through IDs from function input
- `status` as defined above
- `critical_gap_present`: `true` when at least one must-have competency is missing
- `must_have_coverage`:
  - count summary for must-have requirements only
  - `coverage_ratio = matched_count / total_count` (or `0.0` when no must-have requirements)
- `totals`:
  - earned/max points
  - counts for requirements, matched, insufficient, missing
- `weights_used`:
  - priority weights map
  - expected level by priority map (as string values)
- `breakdown`: one item per requirement, including seeker level (nullable when missing)
- `missing_competencies`: derived from `breakdown` with `status == "missing"`
- `insufficient_competencies`: derived from `breakdown` with `status == "insufficient"`
- `development_targets`: derived from non-matched requirements (`missing` + `insufficient`), each with:
  - expected level as `suggested_target_level`
  - `point_gain_if_reached = point_loss`

## Detailed Implementation Design

### 1) Engine constants and helper mappings

In `backend/app/modules/matching/engine.py`, define internal constants:

- `PRIORITY_WEIGHTS`
- `LEVEL_NUMERIC`
- `EXPECTED_LEVEL_BY_PRIORITY`
- `PRIORITY_SORT_RANK`

Keep constants close to function entry for readability and auditability.

### 2) Seeker competency lookup

Build a dictionary from seeker competencies keyed by `competency_key`.

Determinism decision for duplicates in input array (if ever encountered before step 4 guards):

- first occurrence wins
- later duplicates ignored

Rationale: stable behavior without introducing extra policy during step 3.

### 3) Requirement evaluation pipeline

For each requirement in input order:

- resolve static mapping values
- evaluate as missing/present
- build one normalized internal row including all derived fields used later for:
  - breakdown
  - category lists
  - totals
  - sorting

This avoids recomputation and ensures consistent numbers across all output sections.

### 4) Sorting strategy

Create one sort key helper:

- `priority_rank` from mapping
- negative `point_loss` for descending order
- `competency_key`

Use this shared sort for:

- final `breakdown`
- `missing_competencies`
- `insufficient_competencies`
- `development_targets`

### 5) Totals and rounding policy

- compute numeric totals from evaluated rows
- compute score only once, rounded to 1 decimal
- keep points as floats in payload

### 6) Empty requirement behavior

If requirements list is empty:

- return valid payload with empty lists and zero counts
- `status = "not_applicable_no_requirements"`
- `score = 0.0`

No exceptions should be raised for this case.

## File-Level Change Plan

### File 1: `backend/app/modules/matching/engine.py`

Changes:

- remove `NotImplementedError` stub
- implement full deterministic calculation
- keep function pure (no DB/session, no external calls)
- optionally add small private helper functions for:
  - sort key creation
  - row conversion to schema models

No changes to public function signature.

### File 2: `backend/tests/test_matching_engine.py` (new)

Add unit tests for deterministic engine behavior.

Test cases:

1. `test_full_match_returns_100_score_and_no_gaps`
2. `test_missing_competency_is_classified_and_scored_as_zero`
3. `test_insufficient_level_gets_partial_points`
4. `test_weighted_mixed_priorities_score_is_correct`
5. `test_no_requirements_returns_not_applicable_status`
6. `test_output_ordering_is_deterministic_across_lists`

Keep tests purely unit-level by calling engine function directly with schema inputs.

## Test Execution Plan

Virtual environment for testing is located in:

- `/Users/andvil/Dev/competency-hiring/backend/.venv`

Primary:

- `pytest backend/tests/test_matching_engine.py`

Regression confidence pass:

- `pytest backend/tests`

## Acceptance Criteria for Step 3 Completion

Step 3 is complete when all are true:

1. `calculate_exact_match_result(...)` returns valid `MatchingResultPayload` for all planned scenarios.
2. Score and point calculations follow the fixed Phase 3 formulas exactly.
3. Output ordering is deterministic according to defined sort rules.
4. Empty requirements case returns `not_applicable_no_requirements` with score `0.0`.
5. New matching engine unit tests pass.
6. Existing backend tests continue to pass.

## Assumptions and Defaults

- enum values in models remain unchanged (`RequirementPriority`, `CompetencyLevel`).
- no overqualification bonus above requirement max points.
- algorithm identifiers remain:
  - `algorithm_version = "v2_exact_priority_level_dual_signal"`
  - `scope = "private_preview"`
- strict validation hardening and defensive enum/duplicate handling is deferred to Phase 3 step 4.

## Risks and Mitigations

Risk: floating-point edge differences across derived sections.

Mitigation:

- compute `earned_points` and `point_loss` once per requirement
- reuse same computed values across all payload sections

Risk: inconsistent ordering between lists.

Mitigation:

- use one shared sorting helper for all output collections

Risk: accidental business logic drift during later steps.

Mitigation:

- keep this file as normative step-3 reference
- ensure tests assert both score and explanation structure

## Next Step After This Plan

After implementing this step, proceed to Phase 3 step 4 for validation and edge-case hardening before wiring seeker endpoint and application snapshot integration.
