from neo4j import Driver, GraphDatabase

from app.core.settings import Settings, get_settings

_driver: Driver | None = None


def get_neo4j_driver(settings: Settings | None = None) -> Driver:
    global _driver

    if _driver is None:
        active_settings = settings or get_settings()
        _driver = GraphDatabase.driver(
            active_settings.neo4j_uri,
            auth=(
                active_settings.neo4j_username,
                active_settings.neo4j_password,
            ),
        )

    return _driver


def close_neo4j_driver() -> None:
    global _driver

    if _driver is not None:
        _driver.close()
        _driver = None
