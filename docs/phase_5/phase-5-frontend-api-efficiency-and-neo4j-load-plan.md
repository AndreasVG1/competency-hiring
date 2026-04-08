# Phase 5 Plan: Frontend API Call Efficiency + Neo4j Load Reduction (Detailed)

## Summary

This document defines an implementation plan to reduce API call volume, backend load (especially Neo4j load), and improve perceived UI speed.

The current frontend has a classic **N+1** pattern for competency label/activity-indicator hydration: a single view can trigger tens or hundreds of calls to:

- `GET /api/v1/catalog/competencies/{competency_key}`

This is expensive because the catalog module queries Neo4j, and the “detail” endpoint also expands activity indicators.

### Primary goal

Replace per-key hydration with **batch resolution** and caching so most pages perform:

- **1 catalog resolve call per page load** (or fewer), and
- **0** competency-detail calls unless the user explicitly opens an “indicators” overlay.

### Non-goals / guardrails

- No changes to matching logic, explanation generation, scoring, or consent/visibility rules.
- No related-competency inference, semantic expansion, embeddings, or similarity ranking.
- Maintain modular monolith boundaries and keep route handlers thin.

---

## Current Baseline (What Happens Today)

### Where calls originate

Frontend API access is centralized in:

- `frontend/src/api/httpClient.ts` (wrapper around `fetch`)
- `frontend/src/api/catalogClient.ts`, `frontend/src/api/seekerClient.ts`, `frontend/src/api/recruiterClient.ts`, `frontend/src/api/authClient.ts`

Most screens load data on `onMounted()` or a `watch(..., { immediate: true })`.

### Biggest inefficiency: per-key competency hydration

The label cache composable:

- `frontend/src/composables/useCatalogLabelCache.ts`

hydrates labels by calling `catalogClient.getCompetency(key)` **once per competency key**. Pages that call `hydrateKeys([...])` can create large request bursts because `hydrateKeys()` uses `Promise.all(...)`.

Common flows that trigger this burst:

- seeker profile overview loads saved competencies then hydrates all keys
- seeker edit view loads competency list then hydrates all keys
- job offer detail hydrates all requirement keys and then hydrates analysis explanation keys after analysis
- recruiter job offer detail hydrates requirement keys
- recruiter applicants hydrates shared profile competency keys and explanation keys

### Why it is costly (Neo4j)

Catalog endpoints are backed by Neo4j, for example:

- `backend/app/modules/catalog/repository.py`

`GET /catalog/competencies/{key}` currently expands activity indicators via an `OPTIONAL MATCH`, which is correct for detail screens but too expensive to call repeatedly just to show a table label.

---

## Target Outcomes (Success Criteria)

### API call volume

For pages with many competencies:

- Reduce catalog calls from **O(N)** to **O(1)** per page load.
- Avoid “burst” patterns (50–200 concurrent calls) that can saturate backend workers and Neo4j connection pools.

### UX / perceived performance

- Tables render quickly with stable labels (or safe fallbacks) without waiting on many requests.
- Typeahead searches feel responsive and do not queue backend work for stale queries.

### Backend scalability

- Replace many Neo4j sessions/queries with a single batched query per page.
- Keep a bounded “max keys per request” limit to prevent large payloads from becoming a new bottleneck.

---

## Locked Product Decisions (Phase 5)

1. **Batch resolve returns only what the UI needs for tables**:
   - `key`, `label`, and `activity_indicator_count`.
   - It does **not** return full activity indicator texts (those remain detail-only).
2. **Lazy-load competency detail only when needed**:
   - Full activity indicator texts are fetched only when user opens an overlay.
3. **Batching is additive, not breaking**:
   - Existing endpoints remain supported.
4. **Privacy boundaries remain intact**:
   - No new recruiter visibility beyond what is already consent-shared.

---

## Implementation Plan (Phased)

This plan is intentionally phased so we can measure improvements after each step and avoid large cross-cutting changes.

### Phase 5.1 — Biggest Win: New Catalog Bulk Resolve API

#### What we add (API design)

Add a new endpoint:

- `POST /api/v1/catalog/competencies/resolve`

Purpose:

- Resolve many competency keys in **one** request for table rendering.
- Provide `activity_indicator_count` so the UI can decide whether to show “View indicators” without loading full indicator text.

#### Request/response contract

Request:

```json
{ "keys": ["comp_1", "comp_2"] }
```

Response:

```json
{
  "items": [
    { "key": "comp_1", "label": "Alpha", "activity_indicator_count": 2 }
  ],
  "missing_keys": ["comp_unknown"]
}
```

Decisions:

- **Deterministic order:** `items` preserve the caller’s first-occurrence key order.
- **Bounded size:** enforce a server-side maximum (default: 500 keys).
- **No internal IDs:** keep current “no Neo4j internal id” rule.

#### Backend work items

1. **Schemas** (`backend/app/modules/catalog/schemas.py`)
   - Add `CompetencyResolveRequest`
   - Add `ResolvedCompetencyItem`
   - Add `CompetencyResolveResponse`
   - Reasoning: explicit schema keeps the contract stable and testable.

2. **Repository** (`backend/app/modules/catalog/repository.py`)
   - Add `resolve_competencies(keys: list[str]) -> list[dict]`
   - Use one Neo4j query with `UNWIND $keys AS key`
   - Compute indicator counts via `count(ai)` rather than collecting full nodes.
   - Reasoning: one query avoids N sessions and returns only what the UI needs.

3. **Service layer** (`backend/app/modules/catalog/service.py`)
   - Add `resolve_competencies(keys: list[str]) -> dict`
   - Normalize keys (trim, remove empties, dedupe while preserving order).
   - Reasoning: keep business rules out of routers; keep router thin.

4. **Router** (`backend/app/modules/catalog/router.py`)
   - Add route handler for the new endpoint.
   - Reasoning: keep response model validation and auth consistent with existing catalog endpoints.

#### Tests (backend)

Add/extend tests in:

- `backend/tests/test_catalog_api.py`

Coverage:

- requires authentication (401 without token)
- deterministic response shape + ordering
- does not leak forbidden id fields
- returns missing keys explicitly

Reasoning:

- This change is purely additive but high impact; tests prevent regressions and accidental ID leakage.

---

### Phase 5.2 — Frontend Wins (Batching + Cache + Cancellation)

Phase 5.2 adopts the new bulk endpoint, adds a global cache, and fixes request waste in typeahead.

#### 5.2.1 Global catalog cache (Pinia)

Create a global store (example path):

- `frontend/src/stores/catalogCache.ts`

Store responsibilities:

- Cache resolved competency meta (`key -> label, activity_indicator_count, loadedAt`).
- Cache competency detail payloads when fetched (for overlay).
- Deduplicate in-flight resolve/detail requests.
- Implement chunking for large key lists (e.g. 200 keys per request).

Reasoning:

- Today, each view instantiates its own cache, so navigation causes redundant re-fetching.
- A global store provides cross-route reuse and makes “batch then lazy detail” easy to centralize.

#### 5.2.2 Replace per-key hydration with a single resolve call

Update view code paths that currently call:

- `labelCache.hydrateKeys(keys)`

to instead call:

- `catalogCache.resolveCompetencies(uniqueKeys)`

Target views:

- `frontend/src/views/seeker/SeekerHomeView.vue`
- `frontend/src/views/seeker/SeekerEditView.vue`
- `frontend/src/views/seeker/SeekerJobOfferDetailView.vue`
- `frontend/src/views/recruiter/RecruiterJobOfferDetailView.vue`
- `frontend/src/views/recruiter/RecruiterJobOfferApplicantsView.vue`

Reasoning:

- This is where the N+1 pattern manifests most strongly.

#### 5.2.3 Make “View indicators” lazy (detail fetch on demand)

Update table components so they do not rely on a prehydrated list of indicators to show the button.

Approach:

- Use `activity_indicator_count > 0` (from resolve meta) to show the “View indicators” button.
- When clicked:
  - call `catalogCache.fetchCompetencyDetail(key)`
  - then show overlay with `detail.activity_indicators`.

Target components:

- `frontend/src/components/CompetencyLevelTable.vue`
- `frontend/src/components/JobOfferRequirementsTable.vue`

Reasoning:

- Most users won’t open indicators for every competency; avoid loading text for all keys by default.
- This significantly reduces Neo4j relationship expansion work.

#### 5.2.4 True request cancellation for typeahead search

Today, `CatalogSearchPicker.vue` ignores stale responses, but the backend still processes them.

Change:

- Add `AbortController` in `frontend/src/components/CatalogSearchPicker.vue`
- Update `searchFn` contract to accept `signal`:
  - from: `searchFn(query) => Promise<CatalogItem[]>`
  - to: `searchFn(query, options?: { signal?: AbortSignal }) => Promise<CatalogItem[]>`
- Update `catalogClient.listCompetencies/listOccupations` to accept and pass `signal` into `apiRequest`.

Reasoning:

- Aborting stale queries prevents wasted Neo4j work during rapid typing.
- This improves responsiveness under load and reduces tail latency.

#### 5.2.5 Concurrency and chunking safeguards

Add guardrails so the app does not create “thundering herd” requests again:

- Do not use unbounded `Promise.all(keys.map(...))` for network calls.
- `resolveCompetencies()`:
  - dedupe keys
  - chunk requests
  - optionally limit concurrent chunks (e.g. 2–4 concurrent)

Reasoning:

- Avoid saturating browser connection limits and backend worker queues.

#### Frontend validation

Run:

- `npm run type-check` (frontend)
- `npm run build` (frontend)

Manual QA (Network tab):

- Seeker home/edit with 50+ competencies:
  - expect 1 resolve request (plus 0 detail calls unless overlay opened)
- Recruiter applicants:
  - expect 1 resolve request covering both shared profile competency keys and explanation keys
- Search picker:
  - rapid typing shows canceled requests

---

### Phase 5.3 — Even Better: Embed Labels/Counts Into Business APIs (Minimize Catalog Calls Further)

Phase 5.3 goes beyond batching and reduces catalog calls by **enriching business endpoints** with the display fields the UI needs.

#### Goal

Make common pages render without any catalog resolve call, by including:

- `competency_label`
- `activity_indicator_count`

directly in responses that already return competency keys.

#### Backend changes (additive fields)

Add optional fields (keep old fields intact):

1. `SeekerCompetencyResponse` (`backend/app/modules/seeker/schemas.py`)
   - add `competency_label: str | None`
   - add `activity_indicator_count: int | None`

2. `JobOfferRequirementResponse` (`backend/app/modules/recruiter/schemas.py`)
   - add the same two fields

3. `PublicJobOfferRequirementItem` (`backend/app/modules/seeker/schemas.py`)
   - add the same two fields

Implementation pattern:

1. Fetch base rows from SQLite as today.
2. Collect unique competency keys from the result set.
3. Call `catalog.resolve_competencies(keys)` once (Phase 5.1 API/service), not per item.
4. Merge labels/counts into response models.

Reasoning:

- This turns the catalog into an internal enrichment step and removes the need for the UI to do it.
- It also simplifies frontend code and makes rendering more predictable.

#### Frontend changes for “even better”

- Prefer `competency_label` and `activity_indicator_count` when present.
- Fall back to the global store’s `resolveCompetencies()` when fields are missing (backwards compatibility during rollout).

#### Notes about explanation keys

Matching explanation payloads currently include competency keys inside:

- highlights
- gaps
- development roadmap (seeker)

These are still likely to need a resolve step unless Phase 5.3 is extended to also embed labels in explanation structures.

Decision for Phase 5:

- Do **not** enrich explanation payloads in this pass (avoid scope creep).
- Continue to resolve explanation keys via the bulk endpoint only when needed.

---

## Rollout Sequence (Decision-Complete)

1. Implement Phase 5.1 backend bulk resolve endpoint + tests.
2. Implement Phase 5.2 frontend global cache + batch usage + lazy indicator detail + typeahead cancellation.
3. Verify measured reduction in requests and stable UI rendering.
4. Implement Phase 5.3 backend enrichment for the highest-traffic endpoints:
   - seeker competencies list
   - recruiter requirements list
   - seeker job-offer detail requirements
5. Update frontend to use enriched fields as preferred fast-path.

---

## Risk Register + Mitigations

1. **Large payloads / long requests**
   - Mitigation: chunking (frontend) + max keys validation (backend).

2. **Cache staleness**
   - Mitigation: treat catalog labels as mostly stable; optionally add TTL-based refresh later if needed.

3. **UI regressions (missing labels)**
   - Mitigation: keep clear fallbacks:
     - show key when label missing
     - show “Label unavailable” for error state

4. **Neo4j pressure shifts**
   - Mitigation: batch resolve uses a single query; monitor query time and ensure indexes/constraints exist on `Competency.id` (follow-up if needed).

---

## Acceptance Checklist

- Pages with many competencies no longer trigger per-key calls to `GET /catalog/competencies/{key}`.
- Initial load for competency-heavy pages performs at most:
  - 1 resolve call + 0 detail calls.
- Opening an indicators overlay triggers at most:
  - 1 detail call for that competency key.
- Typeahead searches abort stale requests.
- Backend tests cover the new bulk endpoint contract.

