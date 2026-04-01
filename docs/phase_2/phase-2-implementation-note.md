# Phase 2 Implementation Note

## Chosen Stack

- Backend: Python + FastAPI
- Backend data access: SQLAlchemy + Alembic
- Frontend: Vue 3 + Vite
- Business data store: SQLite
- Competency catalog store: Neo4j

## Phase 2 Scope

This phase delivers the first seeker-to-recruiter interaction flow while preserving privacy and explicit consent:

- recruiter publish/archive workflow for job offers
- seeker-facing marketplace for published job offers (list/detail + basic filtering)
- consent-based application flow
- recruiter applicant visibility only after seeker application
- application-time snapshot of shared seeker data for auditability

Phase 2 is split into two milestones:

- Milestone 2A: publish workflow + seeker marketplace
- Milestone 2B: applications + consent snapshot + recruiter applicants

The system remains decision-supporting only; no hiring decisions or automated candidate ranking are introduced.

## Out of Scope in Phase 2

The following are explicitly deferred to Phase 3:

- matching score calculation
- matched/missing competency explanations
- recommendation/ranking logic
- related-competency or semantic inference

Also out of scope in Phase 2:

- recruiter browsing of all seeker profiles
- direct runtime dependency on external competency sources

## Structural Direction

- Keep backend route handlers thin and business rules in service/domain logic.
- Keep visibility and consent checks centralized and testable.
- Keep SQLite as the source of truth for business/application records.
- Keep Neo4j as the source of truth for competency catalog read models.
