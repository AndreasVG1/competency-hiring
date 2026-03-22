from neo4j import GraphDatabase
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


def main() -> None:
    if not URI or not USERNAME or not PASSWORD:
        raise ValueError("Missing Neo4j environment variables.")

    with GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD)) as driver:
        driver.verify_connectivity()

        records, summary, keys = driver.execute_query(
            "RETURN 'Neo4j connection works' AS message",
            database_=DATABASE,
        )

        print(records[0]["message"])


if __name__ == "__main__":
    main()
