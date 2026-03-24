# Neo4j Knowledge Graph Structure

## Purpose
This graph stores occupation-specific competency data for a competency-based matching application.

The MVP uses **competencies as the matching unit**. Lower levels are stored mainly for explanation and future extensions.

## Node Types

### `Occupation`
Represents a job role or occupational group.

**Fields**
- `id` (string, required, unique)
- `name` (string, required)

### `Competency`
Represents a high-level competency shown to users in profiles and job requirements.

**Fields**
- `id` (string, required, unique)
- `name` (string, required)
- `ekr_level` (integer, optional)
- `code` (string, required, unique)

### `ActivityIndicator`
Represents a lower-level description that explains what a competency includes.

**Fields**
- `id` (string, required, unique)
- `text` (string, required)
- `code` (string, required, unique)

### `CompetencyElement`
Represents the lowest-level element under an activity indicator.

**Fields**
- `id` (string, required, unique)
- `text` (string, required)
- `type` (string, required)  
  Allowed values:
  - `knowledge`
  - `skill`
  - `attitude`

## Relationship Types

### `(:Occupation)-[:REQUIRES_COMPETENCY]->(:Competency)`
Links an occupation to the competencies associated with it.

**Relationship fields**
- none in MVP

### `(:Competency)-[:HAS_ACTIVITY_INDICATOR]->(:ActivityIndicator)`
Links a competency to the activity indicators that describe it.

**Relationship fields**
- none in MVP

### `(:ActivityIndicator)-[:HAS_ELEMENT]->(:CompetencyElement)`
Links an activity indicator to its lowest-level elements.

**Relationship fields**
- none in MVP

## MVP Modeling Rules
- Matching is done **only at the `Competency` level**.
- `ActivityIndicator` and `CompetencyElement` are stored for explanation and future expansion.
- `CompetencyElement.type` supports `knowledge`, `skill`, and `attitude`, even if the first MVP UI focuses mostly on competencies.
- `Occupation -> Competency` should support reuse across occupations.
- `ActivityIndicator -> CompetencyElement` may also support reuse where appropriate.
- Use application-generated stable IDs instead of relying on inconsistent source IDs.
- Do not include `object` as part of the official `CompetencyElement` contract in MVP.
- Enforce `CompetencyElement.type` allowed values (`knowledge`, `skill`, `attitude`) during ingest/import.

## Example Path
`Occupation -> Competency -> ActivityIndicator -> CompetencyElement`

## Cypher: Clean-Slate Setup (Dev/Test)

Use this only in a development/test database.

### 1) Create constraints for the MVP graph contract

```cypher
CREATE CONSTRAINT occupation_id_unique IF NOT EXISTS
FOR (o:Occupation)
REQUIRE o.id IS UNIQUE;

CREATE CONSTRAINT competency_id_unique IF NOT EXISTS
FOR (c:Competency)
REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT competency_code_unique IF NOT EXISTS
FOR (c:Competency)
REQUIRE c.code IS UNIQUE;

CREATE CONSTRAINT activity_indicator_id_unique IF NOT EXISTS
FOR (a:ActivityIndicator)
REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT activity_indicator_code_unique IF NOT EXISTS
FOR (a:ActivityIndicator)
REQUIRE a.code IS UNIQUE;

CREATE CONSTRAINT competency_element_id_unique IF NOT EXISTS
FOR (e:CompetencyElement)
REQUIRE e.id IS UNIQUE;
```

### 2) Seed minimal example data (contract-aligned)

```cypher
MERGE (o:Occupation {id: 'occ_ster_tehnik'})
SET o.name = 'Sterilisatsioonitehnik';

MERGE (c:Competency {id: 'comp_1'})
SET c.name = 'Meditsiiniseadmete funktsionaalsuse kontroll ja hooldamine',
    c.ekr_level = 4,
    c.code = 'COMP-001';

MERGE (a:ActivityIndicator {id: 'ai_1_1'})
SET a.text = 'Kuivatab pestud ja desinfitseeritud meditsiiniseadmed vastavalt asutusesisesele tööjuhendile.',
    a.code = 'AI-001';

MERGE (e:CompetencyElement {id: 'ce_1_1_1'})
SET e.text = 'Teab seadmete materjalide eripära.',
    e.type = 'knowledge';

MERGE (o)-[:REQUIRES_COMPETENCY]->(c);
MERGE (c)-[:HAS_ACTIVITY_INDICATOR]->(a);
MERGE (a)-[:HAS_ELEMENT]->(e);
```

### 3) Enforce allowed `CompetencyElement.type` during ingest/import

Constraint-level enum checks are not relied on here; enforce allowed values in import queries.

```cypher
UNWIND $rows AS row
WITH row
WHERE row.type IN ['knowledge', 'skill', 'attitude']
MERGE (e:CompetencyElement {id: row.id})
SET e.text = row.text,
    e.type = row.type;
```

If you want invalid rows to fail hard instead of being skipped, validate in the importer before sending Cypher, or run a pre-check query first.

### 4) Search indexes for searching by name or text

```cypher
CREATE INDEX occupation_name_idx IF NOT EXISTS
FOR (n:Occupation)
ON (n.name);

CREATE INDEX competency_name_idx IF NOT EXISTS
FOR (n:Competency)
ON (n.name);

CREATE INDEX activity_indicator_text_idx IF NOT EXISTS
FOR (n:ActivityIndicator)
ON (n.text);

CREATE INDEX competency_element_text_idx IF NOT EXISTS
FOR (n:CompetencyElement)
ON (n.text);
```