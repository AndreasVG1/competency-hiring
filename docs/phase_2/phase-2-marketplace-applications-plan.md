# Phase 2 Plan: Published Job Marketplace + Consent-Based Applications

## Summary

Build the next vertical slice so that:
- recruiters can publish and archive job offers
- job seekers can browse only published job offers
- job seekers can apply to a published offer with explicit consent
- recruiters can view applicants only for their own job offers
- matching/explanation logic remains out of scope for this phase

This phase delivers the first privacy-safe seeker-to-recruiter interaction path while preserving MVP principles:
- transparent workflows
- explicit consent
- strict visibility boundaries
- deterministic, auditable behavior

## Milestone Breakdown

### Milestone 2A: Publish Workflow + Seeker Job Marketplace
Goal:
- move from draft-only offers to controlled publication and seeker discovery

### Milestone 2B: Applications + Consent Snapshot + Recruiter Applicants
Goal:
- enable explicit-consent applications and recruiter applicant visibility without matching logic

## Scope and Non-Goals

### In scope
- recruiter publish/archive actions
- seeker-facing published offer list/detail views with basic filtering
- application submission with explicit consent recording
- recruiter applicant list for owned job offers only
- application-time snapshot of shared seeker data

### Out of scope
- suitability score calculation
- matched/missing competency explanations
- automated ranking, screening, or candidate recommendations
- semantic/related-competency inference
- recruiter browsing of all seeker profiles

## Step-by-Step Tasks

1. [X] Create Phase 2 implementation note and boundaries
- Add a short implementation note in `docs/phase_2/` describing goals, milestones, and explicit non-goals.
- Confirm that matching and explanation are deferred to Phase 3.
- Confirm that this phase is decision-support plumbing, not hiring automation.

2. [X] Add publish/archive business rules to recruiter job offers (Milestone 2A)
- Keep creation and editing in `draft` by default.
- Add explicit service-layer transitions:
- `draft -> published`
- `published -> archived`
- Reject invalid transitions with clear validation errors.
- Keep route handlers thin; put transition rules in recruiter/domain service functions.

3. [ ] Add recruiter publish/archive endpoints (Milestone 2A)
- Add action endpoints under recruiter ownership routes.
- Enforce ownership check before status change.
- Return structured errors for missing/non-owned offers and invalid transition attempts.
- Keep existing recruiter CRUD endpoints intact.

4. [ ] Define seeker-facing published offer read models (Milestone 2A)
- Create read models for:
- list card (id, title, occupation, short description, company_name, published_at)
- detail view (full description, requirements, recruiter/company display fields allowed for seekers)
- Expose only fields needed for seeker browsing; avoid leaking internal-only recruiter data.

5. [ ] Implement seeker published-offer list/detail APIs (Milestone 2A)
- Add list endpoint for published offers only.
- Add detail endpoint for published offers only.
- Support basic deterministic filters:
- free-text query (title/description)
- occupation key
- optional pagination parameters (`limit`, `offset`) for stable scaling
- Ensure seeker role enforcement on these endpoints.

6. [ ] Build seeker marketplace UI (Milestone 2A)
- Add seeker routes:
- `/seeker/job-offers`
- `/seeker/job-offers/{id}`
- Implement list page with:
- search input
- occupation filter
- status badge or clear "Published" context
- Implement detail page with requirements and clear CTA area for future apply action.
- Keep UI language transparent and avoid implied "fit score" messaging in this phase.

7. [ ] Update recruiter UI for publish/archive control (Milestone 2A)
- Show offer status clearly (`draft`, `published`, `archived`) in recruiter list/detail views.
- Add publish/archive actions in offer detail/edit pages with confirmation for risky transitions.
- Keep edit behavior predictable:
- allow editing draft offers
- define and enforce policy for published/archived edits (recommended: edit in any state, but explicit re-publish if required by policy)

8. [ ] Add Milestone 2A backend/frontend tests and acceptance checks
- API tests: status transitions, invalid transitions, ownership checks.
- API tests: seeker list/detail only returns published offers.
- Frontend checks: seeker can browse published offers; recruiter can publish/archive owned offers.

9. [ ] Define application and snapshot domain model (Milestone 2B)
- Add `applications` table in SQLite with:
- `id`
- `job_offer_id` (FK)
- `seeker_user_id` (FK)
- `consent_given_at` (timestamp)
- `created_at` (timestamp)
- Unique constraint on (`job_offer_id`, `seeker_user_id`) to prevent duplicate applications.
- Add snapshot persistence (preferred: dedicated snapshot table keyed by `application_id`, or JSON snapshot columns with clear schema).
- Snapshot should represent what recruiter is allowed to see at apply time.

10. [ ] Implement consent-aware application service (Milestone 2B)
- Add service function to apply to a published offer:
- verify seeker role and ownership context
- verify offer is currently `published`
- verify seeker profile exists before apply
- verify no existing application for same seeker+offer
- record explicit consent timestamp
- persist snapshot payload of seeker profile + competencies (and optional offer metadata for audit)
- Keep consent and visibility logic centralized in service layer.

11. [ ] Add seeker application endpoints (Milestone 2B)
- `POST` apply endpoint for a published offer.
- Optional seeker endpoint to list own applications for UX continuity.
- Return clear conflict response for duplicate apply attempts.

12. [ ] Add recruiter applicants endpoints with strict ownership checks (Milestone 2B)
- Add endpoint for recruiter to list applicants for one owned job offer.
- Response should be derived from application snapshot data, not live seeker profile reads.
- Recruiters must never see non-applicant seeker data.
- Recruiters must never access applicants for non-owned offers.

13. [ ] Build apply + applicants frontend flows (Milestone 2B)
- Seeker detail page:
- add explicit consent text near `Apply`
- require intentional apply action (no hidden implicit consent)
- show apply success and duplicate-apply feedback
- Recruiter views:
- add applicants page for each offer (for example `/recruiter/job-offers/{id}/applicants`)
- show snapshot fields clearly as "shared at application time"

14. [ ] Add Milestone 2B tests (privacy and audit critical)
- API tests:
- seeker cannot apply to `draft`/`archived` offers
- duplicate apply returns conflict
- recruiters cannot view applicants of non-owned offers
- non-recruiters cannot access recruiter applicant endpoints
- Snapshot integrity tests:
- after applying, seeker updates profile/competencies
- recruiter still sees original application snapshot
- End-to-end tests:
- recruiter publishes offer -> seeker discovers -> seeker applies -> recruiter sees applicant

15. [ ] Finalize Phase 2 docs and release checklist
- Update docs with final endpoint list and route map.
- Add a short "known limitations" note (no matching yet).
- Record migration and rollback notes for the new application tables.

## Public APIs and Types

Base API route prefix:
- `/api/v1/`

Recommended new backend routes:
- `POST /recruiter/job-offers/{id}/publish`
- `POST /recruiter/job-offers/{id}/archive`
- `GET /seeker/job-offers?query=...&occupation_key=...&limit=...&offset=...`
- `GET /seeker/job-offers/{id}`
- `POST /seeker/job-offers/{id}/apply`
- `GET /recruiter/job-offers/{id}/applicants`

Optional routes:
- `GET /seeker/applications`
- `GET /recruiter/job-offers/{id}/applications/{application_id}`

Frontend routes to add:
- `/seeker/job-offers`
- `/seeker/job-offers/{id}`
- `/recruiter/job-offers/{id}/applicants`

Important public types to extend:
- `JobOfferStatus = draft | published | archived`
- `PublicJobOfferListItem`
- `PublicJobOfferDetail`
- `ApplicationCreateResponse`
- `RecruiterApplicantListItem` (snapshot-based fields)

## Data Ownership and Privacy Rules for Phase 2

- SQLite remains source of truth for business/application data (`job_offers`, `applications`, snapshots).
- Neo4j remains source of truth for catalog metadata (occupation/competency labels and keys).
- No runtime external source dependency is introduced in this phase.
- Recruiter applicant views must use consent-created application records and snapshots only.
- Job seeker private analysis does not exist yet; therefore nothing beyond application-approved profile data is shared.

## Test Plan

- Role/access:
- seeker cannot call recruiter-only publish/archive/applicant endpoints
- recruiter cannot call seeker-only apply endpoints
- Publication:
- only owner can publish/archive an offer
- invalid status transitions fail with structured errors
- seeker list/detail includes only published offers
- Application:
- apply succeeds only for published offers
- duplicate apply is blocked with `409`
- applying records `consent_given_at`
- Visibility:
- recruiter sees applicants only for owned offers
- recruiter cannot browse all seekers
- Snapshot:
- recruiter applicant response reflects snapshot, not mutable live seeker state

## Assumptions and Defaults

- Existing recruiter offer CRUD remains intact; status transitions are additive.
- Offer requirements continue to be managed as in Phase 1.
- Candidate pipeline stages (reviewed/rejected/accepted) are deferred.
- Notification/email workflow is deferred.
- Matching and explanation begin only after Phase 2 privacy-safe application flow is stable.
