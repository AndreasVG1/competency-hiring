# Phase 4 Implementation Note

## Chosen Stack

- Backend: Python + FastAPI
- Backend data access: SQLAlchemy + Alembic
- Frontend: Vue 3 + Vite
- Business data store: SQLite
- Competency catalog store: Neo4j

## Phase 4 Scope (Backend Completed)

Phase 4 adds a dedicated explanation layer on top of deterministic matching results:

- explanation module under `backend/app/modules/explanation`
- seeker analysis response enriched with explanation
- recruiter applicant shared matching enriched with recruiter-safe explanation
- role-aware rendering rules (`seeker` vs `recruiter`)
- unknown algorithm fallback explanation behavior
- robustness handling for malformed legacy snapshot payloads

This phase remains decision-supporting only and does not alter matching score logic.

## Implemented Decisions

- Matching remains the canonical scoring source (`modules/matching` unchanged).
- Explanation is generated on read (not persisted).
- Seeker receives development roadmap.
- Recruiter explanation never includes development roadmap.
- API responses keep raw payload and add explanation for transparency.
- Unknown `algorithm_version` returns a minimal fallback explanation instead of failing.
- Invalid legacy snapshot payloads do not break recruiter applicant listing.

## Out of Scope in Phase 4

- chart-based explanation UI
- multilingual explanation templates
- persistence of explanation text snapshots
- semantic/related competency inference
- embeddings, vector search, or black-box recommendation behavior

## Structural Direction

- Keep route handlers thin and keep explanation composition in service layer.
- Keep explanation rendering deterministic and independently testable.
- Keep consent visibility boundaries unchanged:
  - seeker-private analysis remains private
  - recruiter sees explanation only from consent-shared application snapshots

## Known Limitations

- Explanation text is template-based and English-only.
- Fallback explanation for unknown algorithms is intentionally minimal.
- Recruiter-side malformed legacy payloads return `shared_matching.explanation = null` while preserving the applicant row.
