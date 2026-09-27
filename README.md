# Competency Hiring

Competency Hiring is a development-oriented bachelor thesis project exploring transparent, privacy-aware job matching. Job seekers can describe their competencies, review how they compare with a role, and decide whether to apply. Recruiters manage job offers and see a seeker's shared profile and matching snapshot only after an application.

The application is decision support: its rules are deterministic and explainable, and it does not make hiring decisions.

## What it does

- Supports separate job seeker and recruiter accounts.
- Lets job seekers maintain a profile and competency levels, browse published roles, and privately review suitability analyses.
- Lets recruiters create, edit, publish, and archive job offers with prioritized competency requirements.
- Matches exact competency keys using requirement priority and competency level; results include matched, missing, and insufficient competencies with an explanation.
- Records consent when a seeker applies and stores application-time profile and matching snapshots for recruiter review.
- Provides competency and occupation catalog data from an internal Neo4j graph; SQLite stores accounts, profiles, offers, applications, and snapshots.

## Technology

- **Frontend:** Vue 3, TypeScript, Vite, Vue Router, Pinia, Bootstrap
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic
- **Data:** SQLite for application data; Neo4j for the competency catalog
- **Deployment:** Docker multi-stage build with Nginx serving the frontend

## Project structure

```text
backend/
  app/modules/     # auth, seeker, recruiter, catalog, matching, explanation, applications
  app/scripts/     # competency data preparation and graph population
  alembic/         # SQLite schema migrations
  tests/           # service, API, matching, and application tests
frontend/          # Vue application
docs/              # implementation notes and phase plans
```

The backend is organized as a modular monolith. Matching and explanation rules live in focused modules, while API routers expose versioned endpoints under `/api/v1`.

## Run locally

The application requires Python 3.12 or newer, Node.js 20 or newer, and a configured Neo4j database. Copy `.env.example` to `.env` in the repository root and update the Neo4j connection and local JWT secret for your environment. `SQLITE_URL` is optional; by default, SQLite data is stored under `backend/data/`.

Install the backend dependencies and start the API:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In another terminal, install frontend dependencies and start Vite:

```bash
cd frontend
npm ci
npm run dev
```

The API documentation is available at `/docs` on the backend host. The frontend's API base URL can be set with `VITE_API_BASE_URL` at build time; see `frontend/src/api/config.ts`.

For container deployment, the repository includes a `Dockerfile` and `docker-compose.yml`; both require the same environment configuration and an available Neo4j service.

## Tests

Backend tests are in `backend/tests/` and use pytest. The frontend includes build and type-check scripts (`npm run build` and `npm run type-check`).

## Project status

This is an MVP/thesis project under active development. The implemented matching flow uses exact competency matches and deterministic priority/level rules; it does not infer related competencies or use machine learning. The competency graph is populated from prepared source data and is used internally at runtime.
