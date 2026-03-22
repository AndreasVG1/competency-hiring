# Phase 1 Plan: FastAPI + Vue MVP Setup for Profiles

## Summary

Build the first vertical slice of the system so that:
- a registered job seeker can create and maintain a competency profile
- a registered recruiter can create and maintain a job profile/job offer
- both flows use a read-only competency catalog served from Neo4j mock data
- there is no matching, explanation, application, or consent flow yet

This slice should establish the long-term project shape: FastAPI backend, SQLAlchemy + Alembic for SQLite business data, Vue 3 + Vite frontend, thin route handlers, service-layer business logic, and strict role-based access.

## Step-by-Step Tasks

1. Create the project skeleton and documentation
- Add a short implementation note in `docs/` that records the chosen stack and this phase scope.
- Restructure the backend toward `backend/app/{api,core,modules,db}` and the frontend toward a standard Vite Vue app.
- Remove the committed local virtual environment from the tracked project and keep environments outside the repo.

2. Set up backend foundations
- Initialize FastAPI with an app entrypoint, health route, settings module, dependency wiring, CORS, and structured error responses.
- Add dependencies for FastAPI, SQLAlchemy 2.x, Alembic, password hashing, JWT auth, Neo4j driver, and pytest.
- Define environment-based configuration for SQLite URL, Neo4j URL, Neo4j credentials, JWT secret, and frontend origin.

3. Define the Phase 1 domain model in SQLite
- Create `users` with: `id`, `email`, `password_hash`, `role`, `created_at`.
- Create `job_seeker_profiles` with: `user_id`, `full_name`, `summary`, `location`, `created_at`, `updated_at`.
- Create `job_seeker_competencies` with: `id`, `user_id`, `competency_key`, `level`.
- Create `recruiter_profiles` with: `user_id`, `company_name`, `contact_name`.
- Create `job_offers` with: `id`, `recruiter_user_id`, `title`, `description`, `status`, `created_at`, `updated_at`.
- Create `job_offer_requirements` with: `id`, `job_offer_id`, `competency_key`, `priority`.
- Use Alembic from the beginning so schema changes stay reviewable.

4. Define the competency catalog contract
- Treat Neo4j as the source of truth for competency catalog lookup only.
- Require each mock competency node in Neo4j to have a stable `competency_key` and display `label`.
- Store only `competency_key` in SQLite relations; do not store Neo4j internal node IDs.
- Expose catalog search and detail endpoints from the backend so the frontend never talks to Neo4j directly.

5. Implement authentication and authorization
- Build minimal email/password registration and login.
- Assign role at registration: `job_seeker` or `recruiter`.
- Use JWT bearer auth for this phase, with the authenticated user injected into protected endpoints.
- Enforce role checks in backend dependencies so seekers cannot call recruiter routes and recruiters cannot call seeker routes.

6. Implement seeker profile backend
- Add service methods and endpoints to create/read/update the seeker profile.
- Add service methods and endpoints to add, update, list, and remove seeker competencies.
- Restrict access so a seeker can only manage their own profile.
- Validate `level` against an explicit enum, for example: `beginner`, `intermediate`, `advanced`.

7. Implement recruiter job profile backend
- Add service methods and endpoints to create/read/update the recruiter profile.
- Add service methods and endpoints to create/read/update recruiter job offers.
- Add service methods and endpoints to add, update, list, and remove job offer competency requirements.
- Keep job offers in `draft` status only for this phase.
- Validate `priority` against an explicit enum, for example: `must_have`, `important`, `nice_to_have`.

8. Set up frontend foundations
- Initialize Vue 3 + Vite with Vue Router.
- Add a small auth store for current user, token, login state, and role-aware route guarding.
- Create a typed API client layer so UI components stay free of HTTP details.
- Establish two protected areas: seeker routes and recruiter routes.

9. Build the authentication UI
- Create registration and login pages.
- Let the user choose seeker vs recruiter role during registration.
- Persist login state for the session and fetch `/auth/me` on app startup to restore the current user view.

10. Build the seeker profile UI
- Create a seeker dashboard/profile page with personal profile fields.
- Add a competency picker that calls the backend catalog search endpoint.
- Let the seeker add competencies with levels, edit levels, and remove competencies.
- Show the saved competency profile clearly as a list/table.

11. Build the recruiter job profile UI
- Create a recruiter dashboard with a minimal recruiter/company profile form.
- Add a job offer creation page with title, description, and competency requirements.
- Add a competency picker that calls the same catalog search endpoint.
- Let the recruiter add requirements with priority, edit priority, and remove requirements.
- Show saved job offers and allow editing of draft entries.

12. Finish with validation, tests, and acceptance checks
- Add backend unit and API tests before expanding the scope further.
- Manually verify the two end-to-end flows in the browser against the running API.
- Only after both creation flows are stable should matching and explanation work begin.

## Public APIs and Types

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

- `GET /competencies?query=...`
- `GET /competencies/{competency_key}`

- `GET /seeker/profile`
- `PUT /seeker/profile`
- `GET /seeker/competencies`
- `POST /seeker/competencies`
- `PATCH /seeker/competencies/{id}`
- `DELETE /seeker/competencies/{id}`

- `GET /recruiter/profile`
- `PUT /recruiter/profile`
- `GET /recruiter/job-offers`
- `POST /recruiter/job-offers`
- `GET /recruiter/job-offers/{id}`
- `PATCH /recruiter/job-offers/{id}`
- `GET /recruiter/job-offers/{id}/requirements`
- `POST /recruiter/job-offers/{id}/requirements`
- `PATCH /recruiter/job-offers/{id}/requirements/{requirement_id}`
- `DELETE /recruiter/job-offers/{id}/requirements/{requirement_id}`

Important public types:
- `UserRole = job_seeker | recruiter`
- `CompetencyLevel = beginner | intermediate | advanced`
- `RequirementPriority = must_have | important | nice_to_have`
- `JobOfferStatus = draft`

## Test Plan

- Registration creates users with the correct role and hashed password.
- Login returns a valid token and `/auth/me` resolves the correct user.
- Role protection blocks recruiter access to seeker endpoints and seeker access to recruiter endpoints.
- Competency catalog endpoints return Neo4j-backed mock data and reject unknown keys cleanly.
- A seeker can create and update only their own profile.
- A seeker can add, edit, and remove competencies with valid levels.
- A recruiter can create and update only their own recruiter profile.
- A recruiter can create, edit, and list only their own draft job offers.
- A recruiter can add, edit, and remove job requirements with valid priorities.
- Validation errors are returned in structured form for bad payloads and unauthorized access.

## Assumptions and Defaults

- Authentication is included in this first slice and uses email/password + JWT bearer tokens.
- The frontend uses Vue Router and a small auth store; no heavier state architecture is needed yet.
- Neo4j is populated manually with mock competencies and is read-only for this phase.
- SQLite stores business data only; competency catalog data remains in Neo4j and is referenced by stable `competency_key`.
- Recruiter accounts represent a single company context for now.
- Job offers stay in `draft` state only; publish/archive workflows are deferred.
- Matching, explanation, applications, consent snapshots, and the Knowledge Adapter are explicitly out of scope for this phase.
