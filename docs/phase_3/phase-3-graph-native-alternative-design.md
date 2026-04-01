# Phase 3 Alternative Design: Graph-Native KSA Coverage + Transfer Matching

## Purpose

This document describes a deliberate alternative to the official Phase 3 MVP scorer.

It is intentionally more exploratory and graph-native, using the Neo4j structure in `neo4j_graph_structure.md`:
- `Occupation -> Competency -> ActivityIndicator -> CompetencyElement`
- `CompetencyElement.type` in `knowledge | skill | attitude`

The goal is to show how matching could evolve beyond strict enum-driven scoring while staying explainable.

## Why This Alternative Exists

The official Phase 3 MVP uses exact competency matching with deterministic weights (Option 1), which is the right low-risk implementation path.

This alternative exists to support:
- thesis discussion of richer competency intelligence
- future iteration planning after MVP stabilization
- stronger explanation outputs at the `knowledge/skill/attitude` level

## Design Principles

1. Graph-native first
- scoring should use graph structure as input, not only labels.

2. Explainability preserved
- every score component must be traceable to explicit graph evidence.

3. Controlled complexity
- this is still rule-based and auditable, not black-box ML.

4. Privacy unchanged
- seeker-private analysis stays private until apply consent.

## Conceptual Shift from Current MVP

Current MVP assumptions:
- seeker competency level is a 3-step enum
- recruiter requirement strength is a 3-step enum
- exact competency key match dominates

Alternative assumptions:
- seeker competency has confidence score in `[0,1]`
- requirement importance is partly graph-derived
- near-transfer between competencies is allowed when graph evidence overlaps

## Data Model Extensions (Future-Oriented)

These are potential extensions, not immediate MVP requirements.

### Seeker evidence profile
Instead of only storing a single enum level per competency, support:
- `self_assessed_confidence` in `[0,1]`
- optional evidence references (project, course, certification, portfolio)
- optional timestamp and recency decay policy

### Requirement profile
Instead of only manual priority labels, derive additional weight signals from graph structure:
- competency specificity across occupations
- competency depth (number of indicators/elements)
- optional recruiter override factor

### Graph-derived signatures
For each competency `c`, build a signature:
- `A(c)` = activity indicator set
- `E_k(c)` = knowledge elements
- `E_s(c)` = skill elements
- `E_a(c)` = attitude elements

## Core Algorithm

### 1) Exact competency contribution
For required competency `r`:
- `exact(r) = confidence(r)` if seeker has `r`, else `0`

### 2) Transfer contribution from neighboring competencies
Allow partial credit when seeker has competency `s != r` with overlapping KSA evidence.

Compute similarity:

- `sim_k(r,s) = Jaccard(E_k(r), E_k(s))`
- `sim_s(r,s) = Jaccard(E_s(r), E_s(s))`
- `sim_a(r,s) = Jaccard(E_a(r), E_a(s))`

Type-weighted similarity:

- `sim(r,s) = 0.30*sim_k + 0.50*sim_s + 0.20*sim_a`

Best transferable contribution:

- `transfer(r) = max_s(sim(r,s) * confidence(s))`

Transfer cap for conservatism:

- `transfer_capped(r) = min(transfer(r), 0.70)`

### 3) Requirement fulfillment

- `fulfillment(r) = max(exact(r), transfer_capped(r))`

This ensures exact evidence dominates when available.

### 4) Requirement weight (graph-derived)

Given:
- `N_occ` = number of occupations
- `occ_count(r)` = occupations requiring competency `r`
- `depth(r) = 1 + |A(r)| + |E_k(r)| + |E_s(r)| + |E_a(r)|`

Define:
- `specificity(r) = log(1 + N_occ / max(occ_count(r),1))`
- `complexity(r) = log(1 + depth(r))`
- `weight_raw(r) = specificity(r) * complexity(r)`
- `weight(r) = weight_raw(r) / sum(weight_raw(*))`

Optional recruiter override:
- `weight_final(r) = weight(r) * recruiter_override_factor(r)`
- normalize again so weights sum to 1.

### 5) Final score

- `score = 100 * sum_r(weight_final(r) * fulfillment(r))`

### 6) Critical-gap guardrail

Even with good average score, block “strong fit” labels when a highly weighted competency has very low fulfillment.

Example rule:
- if any `r` in top 20% weight has `fulfillment(r) < 0.35`, set flag `critical_gap = true`

## Explainability Output (Richer Than MVP)

For each required competency, return:
- `exact_contribution`
- `transfer_contribution`
- `best_transfer_source_competency`
- per-type overlap (`knowledge`, `skill`, `attitude`)
- missing indicators and missing elements
- potential score gain if target fulfillment threshold is reached

Suggested top-level response fields:
- `algorithm_version`
- `score`
- `critical_gap`
- `weight_method`
- `requirement_breakdown[]`
- `development_roadmap[]`

This enables user-facing statements like:
- "Your score for `comp_x` came mostly from transfer via `comp_y` (shared skill elements)."
- "Raising `comp_z` to target would add +6.4 score points."

## Cypher-Oriented Data Retrieval Pattern

Example pattern for one job offer:

1. Get required competencies.
2. For each required competency, fetch indicators and elements grouped by type.
3. Fetch same signature sets for seeker competencies.
4. Perform similarity and scoring in Python service layer for deterministic control.

Notes:
- keep heavy scoring logic in Python service/domain layer, not inside large Cypher blobs
- keep Neo4j usage read-only for signature assembly

## Evaluation Strategy (Recommended)

### Shadow mode
Before productizing this scorer:
- keep Option 1 as official displayed score
- run graph-native scorer in parallel in backend logs/experiment table
- compare outputs for consistency and explanation quality

### Evaluation dimensions
- stability: does small profile change produce intuitive score movement?
- fairness: does transfer credit over-reward weak evidence?
- explainability: can non-technical users understand top 3 reasons?
- agreement: does it align with recruiter/seeker domain judgment in pilot review?

## Risks and Mitigations

1. Risk: complexity drift beyond thesis scope
- Mitigation: keep this design non-default and behind feature flag.

2. Risk: transfer credit may feel "too magical"
- Mitigation: strict transfer cap and transparent provenance fields.

3. Risk: graph quality inconsistency
- Mitigation: import-time validation and dedup checks in Knowledge Adapter.

4. Risk: performance for large signatures
- Mitigation: precompute competency signatures and cache similarity matrix periodically.

## Adoption Path After MVP

1. Keep Option 1 as production baseline.
2. Implement graph-native scorer in experimental module.
3. Run shadow mode for selected offers.
4. Review explanation quality with stakeholders.
5. If accepted, expose as optional "advanced insight" panel, not default ranking engine.

## Non-Goals for This Alternative

- replacing consent boundaries
- bypassing recruiter ownership checks
- turning the system into automated hiring decision-maker
- introducing opaque machine-learned ranking without clear explanation

## Conclusion

This graph-native design can provide richer competency intelligence and more nuanced development guidance than strict exact-match scoring. It should be treated as a post-MVP extension and validated in shadow mode first, while Option 1 remains the official, deterministic Phase 3 implementation.
