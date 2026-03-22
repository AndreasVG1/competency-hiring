from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "backend" / "data" / "app.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(
        "Competency Hiring API",
        validation_alias="APP_NAME",
    )
    environment: str = Field(
        "development",
        validation_alias="ENVIRONMENT",
    )
    debug: bool = Field(
        False,
        validation_alias="DEBUG",
    )

    sqlite_url: str = Field(
        f"sqlite:///{DEFAULT_SQLITE_PATH}",
        validation_alias="SQLITE_URL",
    )

    neo4j_uri: str = Field(..., validation_alias="NEO4J_URI")
    neo4j_username: str = Field(..., validation_alias="NEO4J_USERNAME")
    neo4j_password: str = Field(..., validation_alias="NEO4J_PASSWORD")
    neo4j_database: str = Field("neo4j", validation_alias="NEO4J_DATABASE")

    jwt_secret: str = Field("change-me", validation_alias="JWT_SECRET")
    frontend_origin: str = Field(
        "http://localhost:5173",
        validation_alias="FRONTEND_ORIGIN",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [self.frontend_origin]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
