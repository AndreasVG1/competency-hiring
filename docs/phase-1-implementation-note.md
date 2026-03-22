# Phase 1 Implementation Note

## Chosen Stack

- Backend: Python + FastAPI
- Backend data access: SQLAlchemy + Alembic
- Frontend: Vue 3 + Vite
- Business data store: SQLite
- Competency catalog store: Neo4j

## Phase 1 Scope

This phase establishes the initial project structure for the MVP profile flows:

- a job seeker profile setup flow
- a recruiter profile and draft job offer setup flow
- a read-only competency catalog exposed by the backend

The following remain out of scope for this phase:

- matching and explanation logic
- consent and application sharing flows
- live runtime calls to external competency sources

## Structural Direction

- The backend is organized as a modular monolith under `backend/app/`.
- The frontend follows a standard Vite Vue application layout under `frontend/`.
- Local virtual environments must stay outside the repository.
