from neo4j import Driver

from app.core.settings import get_settings
from app.db.neo4j import get_neo4j_driver


def _driver_and_database() -> tuple[Driver, str]:
    settings = get_settings()
    return get_neo4j_driver(settings), settings.neo4j_database


def search_competencies(*, query: str, limit: int) -> list[dict]:
    driver, database = _driver_and_database()

    cypher = """
    MATCH (c:Competency)
    WHERE $query = ""
       OR toLower(c.id) CONTAINS toLower($query)
       OR toLower(c.name) CONTAINS toLower($query)
       OR toLower(c.code) CONTAINS toLower($query)
    RETURN c.id AS id, c.name AS name, c.code AS code, c.ekr_level AS ekr_level
    ORDER BY c.name ASC, c.id ASC
    LIMIT $limit
    """

    with driver.session(database=database) as session:
        result = session.run(cypher, {"query": query, "limit": limit})
        return [record.data() for record in result]


def get_competency_by_key(*, competency_key: str) -> dict | None:
    driver, database = _driver_and_database()

    cypher = """
    MATCH (c:Competency {id: $competency_key})
    OPTIONAL MATCH (c)-[:HAS_ACTIVITY_INDICATOR]->(ai:ActivityIndicator)
    WITH c, ai
    ORDER BY ai.text ASC, ai.id ASC
    RETURN
      c.id AS id,
      c.name AS name,
      c.code AS code,
      c.ekr_level AS ekr_level,
      [item IN collect(ai) WHERE item IS NOT NULL | {id: item.id, text: item.text, code: item.code}]
        AS activity_indicators
    LIMIT 1
    """

    with driver.session(database=database) as session:
        record = session.run(cypher, competency_key=competency_key).single()
        if record is None:
            return None
        return record.data()


def resolve_competencies(*, keys: list[str]) -> list[dict]:
    driver, database = _driver_and_database()

    cypher = """
    UNWIND range(0, size($keys) - 1) AS idx
    WITH idx, $keys[idx] AS key
    OPTIONAL MATCH (c:Competency {id: key})
    OPTIONAL MATCH (c)-[:HAS_ACTIVITY_INDICATOR]->(ai:ActivityIndicator)
    RETURN
      idx AS idx,
      key AS requested_key,
      c.id AS id,
      c.name AS name,
      count(ai) AS activity_indicator_count
    ORDER BY idx ASC
    """

    with driver.session(database=database) as session:
        result = session.run(cypher, {"keys": keys})
        return [record.data() for record in result]


def search_occupations(*, query: str, limit: int) -> list[dict]:
    driver, database = _driver_and_database()

    cypher = """
    MATCH (o:Occupation)
    WHERE $query = ""
       OR toLower(o.id) CONTAINS toLower($query)
       OR toLower(o.name) CONTAINS toLower($query)
    RETURN o.id AS id, o.name AS name
    ORDER BY o.name ASC, o.id ASC
    LIMIT $limit
    """

    with driver.session(database=database) as session:
        result = session.run(cypher, {"query": query, "limit": limit})
        return [record.data() for record in result]


def get_occupation_by_key(*, occupation_key: str) -> dict | None:
    driver, database = _driver_and_database()

    cypher = """
    MATCH (o:Occupation {id: $occupation_key})
    OPTIONAL MATCH (o)-[:REQUIRES_COMPETENCY]->(c:Competency)
    WITH o, c
    ORDER BY c.name ASC, c.id ASC
    RETURN
      o.id AS id,
      o.name AS name,
      [item IN collect(c) WHERE item IS NOT NULL | {id: item.id, name: item.name}] AS required_competencies
    LIMIT 1
    """

    with driver.session(database=database) as session:
        record = session.run(cypher, occupation_key=occupation_key).single()
        if record is None:
            return None
        return record.data()
