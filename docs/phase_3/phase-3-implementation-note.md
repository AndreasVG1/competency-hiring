# Phase 3 Implementation Note

## Chosen Stack

- Backend: Python + FastAPI
- Backend data access: SQLAlchemy + Alembic
- Frontend: Vue 3 + Vite
- Business data store: SQLite
- Competency catalog store: Neo4j

## Phase 3 Scope

This phase introduces private, explainable matching while preserving consent and visibility boundaries:

- seeker-private suitability analysis for published job offers
- deterministic exact competency matching (no semantic inference)
- transparent score breakdown for explainability
- missing and insufficient competency feedback
- application-time matching snapshot sharing with recruiters only after consent

The system remains decision-supporting only; it does not make hiring decisions.

## Official Matching Approach for Phase 3

Phase 3 uses the fixed MVP logic from the project plan:

- exact `competency_key` matching only
- deterministic scoring using requirement priority weights and seeker level values
- global expected minimum level by requirement priority
- explainability payload returned with score inputs, per-requirement outcomes, and development targets

This keeps scoring auditable, testable, and aligned with the thesis MVP boundaries.

## Out of Scope in Phase 3

The following are explicitly out of scope for the official Phase 3 implementation:

- related-competency or semantic inference
- graph similarity transfer scoring as default production logic
- embeddings, vector search, or black-box ranking
- recruiter access to seeker-private analysis before consent
- runtime dependence on external competency sources

## Structural Direction

- Keep backend route handlers thin; scoring and explanation facts stay in matching services.
- Keep matching deterministic and independently unit-testable.
- Keep SQLite as source of truth for transactional matching outputs and snapshots.
- Keep Neo4j as read-only catalog/graph source for keys and labels in this phase.
- Preserve strict privacy: private analysis first, consent-gated sharing second.
