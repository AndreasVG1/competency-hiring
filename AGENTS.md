# AGENTS.md

## Purpose

This repository contains a development-oriented bachelor thesis project: a web application for transparent, privacy-aware, competency-based job matching.

The system supports two main user roles:

- **Job Seeker**
- **Recruiter / Employer**

The core idea is:

- the **job seeker owns the analysis**
- matching results are first visible only to the job seeker
- the recruiter sees candidate data **only after explicit consent**, given through applying

This file provides instructions for AI coding agents and contributors working in this repository.

---

## Project Summary

The application is designed as a **layered modular monolith**.

This architectural choice exists because it:

- reduces complexity compared to microservices
- is appropriate for an MVP and bachelor thesis scope
- keeps responsibilities separated
- supports future extension without premature distributed-system complexity

### Main architectural layers

- **User layer**
- **Presentation layer** (frontend)
- **Application layer** (backend modules)
- **Data layer** (SQLite + Neo4j)
- **External integration layer**

---

## Scope and Non-Goals

### In scope

- user authentication and authorization
- job seeker profile management
- recruiter job offer management
- competency selection from knowledge graph data
- private job matching analysis
- transparent explanation of results
- consent-based application flow
- import/sync of external competency data into Neo4j

### Out of scope for MVP

- microservices
- event-driven architecture
- real-time chat
- advanced recommendation engine
- black-box AI ranking of candidates
- automated candidate screening without job seeker action
- recruiter browsing of all job seeker profiles
- direct runtime dependence on the external Semantic MediaWiki source

---

## Core Product Principles

All agents must preserve these principles.

### 1. Transparency over complexity

Matching logic must remain understandable and explainable.

Do not introduce opaque scoring logic without a strong reason and explicit approval.

### 2. Privacy and user control

The job seeker controls whether their data and analysis results are shared.

Recruiters must not gain access to candidate data before consent is given through the application flow.

### 3. Exact-match MVP logic

The MVP matching logic uses **exact competency matching only**.

Do not implement related-competency inference, semantic expansion, embeddings, or similarity-based ranking unless explicitly requested.

### 4. Modular monolith

Keep the backend as a single deployable application, divided into logical modules.

Do not split the system into microservices.

### 5. Clear business logic boundaries

Business rules belong in application/domain services, not in route handlers, UI components, or scattered database queries.

---

## Current Technology Direction

These are the intended technologies unless repository code indicates otherwise.

### Backend
- Python
- FastAPI
- SQLAlchemy
- pytest

### Frontend
- Vue 3 + Vite

### Databases
- SQLite for business/application data
- Neo4j for the internal competency knowledge graph

### Infrastructure
- VPS Docker production deployment
- environment-based configuration

If the implemented stack differs from this section, follow the actual repository code and update this file.

---

## High-Level Domain Model

### User roles

#### Job Seeker
Can:
- create and manage a competency profile
- browse job offers
- run private suitability analysis
- inspect matching results
- decide whether to apply
- control data sharing

#### Recruiter
Can:
- create and manage job offers
- define competency requirements
- prioritize competencies
- view only candidates who have applied
- inspect application-related matching results

### Main modules

#### 1. Authentication & Authorization
Responsibilities:
- registration
- login
- role-based access control
- session/token validation

#### 2. Profile Management
Responsibilities:
- job seeker profile management
- competency addition/removal
- competency level management

#### 3. Job Offer Management
Responsibilities:
- create/edit/archive job offers
- attach competency requirements
- set requirement priority

#### 4. Matching
Responsibilities:
- compare a profile with a job offer
- calculate a suitability score
- identify matched and missing competencies
- keep logic rule-based and explainable

#### 5. Explanation
Responsibilities:
- explain why a score was produced
- present matched competencies
- present missing competencies
- present priority-based development suggestions

#### 6. Application / Consent
Responsibilities:
- apply to a job offer
- record explicit consent
- share application-relevant data with recruiter
- manage candidate lists visible to recruiters

#### 7. Knowledge Adapter
Responsibilities:
- integrate with the external Semantic MediaWiki source
- fetch source data
- normalize and validate data
- import data into Neo4j
- isolate external source specifics from the rest of the system

---

## Data Ownership Rules

These rules are critical.

### SQLite stores business/application data

Examples:
- users
- roles
- job seeker profiles
- job offers
- job offer requirements
- applications
- consents
- matching results
- snapshots of shared data

### Neo4j stores competency graph data

Examples:
- competencies
- skills
- occupations
- qualifications
- related knowledge entities
- relationships between these concepts

### External source usage

The external Semantic MediaWiki source is an **upstream source**, not a runtime dependency for matching.

Required rule:
- data is fetched through the Knowledge Adapter
- data is normalized
- data is stored internally in Neo4j
- runtime matching should rely on internal data, not live external calls

---

## Matching Rules for MVP

These rules must be preserved unless explicitly changed.

### Input
- job offer competencies with priority information
- job seeker competency profile

### Logic
- use **exact matches only**
- do not use related competencies
- do not infer hidden competencies
- transform priority ordering into explicit weights
- calculate a suitability score using deterministic rules

### Output
- suitability score
- matched competencies
- missing competencies
- prioritized development areas
- explanation data suitable for UI display

### Important restriction
The system is **decision-supporting**, not decision-making.

Do not present the system as making hiring decisions.

---

## Consent and Visibility Rules

These are non-negotiable unless the product requirements change.

### Before applying
- the job seeker may run analysis privately
- analysis results are visible only to the job seeker

### When applying
- the system records explicit consent
- the application exposes the allowed profile and analysis data to the recruiter

### Recruiter visibility
- recruiters can only see candidates who have applied
- recruiters must not browse all job seeker profiles
- recruiters must not access private analysis results without consent

### Snapshot preference
Where feasible, treat application-time shared data as a **snapshot** rather than a live mutable view.

Reason:
- improves auditability
- improves consistency
- avoids ambiguity if a profile changes after applying

---

## Repository and Code Organization

Prefer organization by business responsibility, not only by technical layer.

Example target structure:

```text
backend/
  app/
    main.py
    api/
    core/
    modules/
      auth/
      profiles/
      job_offers/
      matching/
      explanation/
      applications/
      knowledge_adapter/
    domain/
    infrastructure/
    tests/

frontend/
docs/
```
---

## Structural Rules

- keep route handlers thin
- keep services focused
- keep database access behind repository/service boundaries where useful
- avoid circular dependencies between modules
- avoid one giant utils.py or helpers.py
- do not place important business rules inside frontend code

---

## Coding Principles

### General

- prefer simple, explicit code over clever abstractions
- prefer readability over premature optimization
- use type hints where practical
- keep functions focused
- write comments only where they add value
- avoid dead code and speculative abstractions

### Business Logic

- place business rules in services/domain logic
- do not bury important rules inside SQL, Cypher, or controllers unless unavoidable
- centralize validation rules
- keep privacy-sensitive logic easy to audit

### API Design

- use clear and consistent request/response models
- return structured validation errors
- use stable field naming conventions
- avoid leaking internal database details in API responses

### Database changes

- keep schema changes small and reviewable
- document any non-obvious modeling decisions
- do not duplicate graph data into SQLite unless there is a clear reason
- do not move transactional business data into Neo4j

### Backend-Specific Rules

- keep route handlers thin
- validate input at API boundaries
- use service layer functions for business operations
- isolate auth logic from domain logic
- isolate Neo4j access from matching service logic where possible
- keep matching deterministic and testable
- avoid global mutable state

### Do Not

- put business logic directly into route files
- make uncontrolled live calls to external data sources from request handlers
- write large untested Cypher queries without explanation
- mix auth, matching, and persistence logic in one function

### Frontend-Specific Rules

The frontend framework may be undecided. Regardless of framework, preserve these rules:

- the frontend communicates only through backend APIs
- the frontend must not access databases directly
- UI logic should stay separate from business rules
- present results clearly and transparently
- clearly distinguish:
    - private analysis
    - application action
    - recruiter-visible data

### UI Priorities for MVP

- clarity
- task completion
- transparency
- minimal friction

### Avoid

- overengineering state management
- complex design systems too early
- hiding important consent actions behind confusing UI patterns

## Knowledge Adapter Rules

This module deserves special care.

### Responsibilities

- fetch data from the external Semantic MediaWiki source
- parse source responses
- normalize data into internal structures
- validate and deduplicate where needed
- import/update Neo4j nodes and relationships

### Rules

- keep external source handling isolated in this module
- do not spread source-specific parsing logic across the codebase
- log failures clearly
- make imports repeatable where possible
- prefer idempotent import/update behavior

### Avoid

- coupling application runtime directly to source availability
- mixing import code into user-facing request handlers
- assuming source data is perfectly clean

---

## Testing Expectations

Every meaningful change should be testable.

### Minimum expectations

- unit tests for business logic
- API/integration tests for major endpoints
- tests for matching rules
- tests for consent/visibility rules
- tests for import normalization where practical

### Highest-priority areas to test

1. matching score logic
2. privacy and access control
3. application/consent flow
4. role-based authorization
5. knowledge import normalization

### When changing matching logic

Always update or add:

- happy path tests
- boundary case tests
- explanation/result tests

## Security And Privacy Expectations

This system handles user-related and potentially sensitive career data.

### Required mindset

- least privilege
- explicit consent
- predictable visibility rules
- careful logging

### Do not

- log passwords, secrets, or raw tokens
- expose private profile data to recruiters before consent
- trust client-side role checks as the only protection
- hardcode secrets
- bypass authorization checks in “temporary” ways

### Preferred practices

- environment variables for secrets
- clear auth middleware/dependencies
- server-side authorization checks
- audit-relevant events recorded where appropriate

---

## Documentation Expectations

When adding non-trivial functionality:

- document major architectural decisions
- document assumptions
- leave concise TODOs where intentional gaps remain

Use docs/ for:

- architecture notes
- API contracts
- diagrams
- import process notes
- thesis-relevant implementation rationale

## Explicit Architecture Constraints

Unless explicitly instructed otherwise, agents must not introduce:

- microservices
- message brokers
- distributed queues
- CQRS/event sourcing
- GraphQL
- websocket-heavy real-time systems
- embedding/vector search infrastructure
- black-box ML ranking
- unnecessary third-party abstractions

Reason:
This is an MVP and bachelor thesis project. Simplicity, explainability, and controlled scope are more important than architectural sophistication.