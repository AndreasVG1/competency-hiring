from neo4j import Driver

from app.core.settings import get_settings
from app.db.neo4j import get_neo4j_driver
from app.scripts.load_excel import OccupationData, get_occupation_data_from_excel
from dataclasses import asdict
from typing import List


def _occupation_to_dict(occupation: OccupationData) -> dict:
    return asdict(occupation)


def _driver_and_database() -> tuple[Driver, str]:
    settings = get_settings()
    return get_neo4j_driver(settings), settings.neo4j_database

def ensure_constraints() -> None:
    driver, database = _driver_and_database()

    statements = [
        "CREATE CONSTRAINT occupation_id_unique IF NOT EXISTS FOR (o:Occupation) REQUIRE o.id IS UNIQUE",
        "CREATE CONSTRAINT competency_id_unique IF NOT EXISTS FOR (c:Competency) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT competency_code_unique IF NOT EXISTS FOR (c:Competency) REQUIRE c.code IS UNIQUE",
        "CREATE CONSTRAINT activity_indicator_id_unique IF NOT EXISTS FOR (a:ActivityIndicator) REQUIRE a.id IS UNIQUE",
        "CREATE CONSTRAINT activity_indicator_code_unique IF NOT EXISTS FOR (a:ActivityIndicator) REQUIRE a.code IS UNIQUE",
    ]

    with driver.session(database=database) as session:
        for stmt in statements:
            session.run(stmt).consume() # type: ignore

def get_graph_counts() -> dict:
    driver, database = _driver_and_database()

    with driver.session(database=database) as session:
        occupations = session.run(
            "MATCH (o:Occupation) RETURN count(o) AS count"
        ).single()["count"] # pyright: ignore[reportOptionalSubscript]

        competencies = session.run(
            "MATCH (c:Competency) RETURN count(c) AS count"
        ).single()["count"] # pyright: ignore[reportOptionalSubscript]

        activity_indicators = session.run(
            "MATCH (a:ActivityIndicator) RETURN count(a) AS count"
        ).single()["count"] # pyright: ignore[reportOptionalSubscript]

        return {
            "occupations": occupations,
            "competencies": competencies,
            "activity_indicators": activity_indicators,
        }
    
def populate_graph(occupation_data: List[OccupationData]) -> None:
    driver, database = _driver_and_database()

    cypher = """
    MERGE (o:Occupation {id: $occupation.id})
    SET o.name = $occupation.name

    WITH o, $occupation.competencies AS competencies
    UNWIND competencies AS comp

    MERGE (c:Competency {id: comp.id})
    SET c.name = comp.name,
        c.ekr_level = comp.ekr_level,
        c.code = comp.code

    MERGE (o)-[:REQUIRES_COMPETENCY]->(c)

    WITH c, comp.activity_indicators AS indicators
    UNWIND indicators AS ai

    MERGE (a:ActivityIndicator {id: ai.id})
    SET a.text = ai.text,
        a.code = ai.code

    MERGE (c)-[:HAS_ACTIVITY_INDICATOR]->(a)
    """

    with driver.session(database=database) as session:
        for occupation in occupation_data:
            session.run(cypher, {"occupation": _occupation_to_dict(occupation)}).consume()
    
if __name__ == "__main__":
    ensure_constraints()
    print("Graph counts before population:")
    counts_before = get_graph_counts()
    print(counts_before)
    occupation_data = get_occupation_data_from_excel(
        file_path="app/scripts/kompetentsid.xlsx",
        sheet_name=0,
        field_filter="IT, TELEKOMMUNIKATSIOON JA ELEKTROONIKA"
    )
    print(f"Loaded {len(occupation_data)} occupations from Excel.")
    populate_graph(occupation_data)
    counts_after = get_graph_counts()
    print("Graph counts after population:")
    print(counts_after)