from pydantic import BaseModel


class CatalogItem(BaseModel):
    key: str
    label: str


class CompetencyCatalogItem(CatalogItem):
    code: str
    ekr_level: int | None = None


class OccupationDetail(CatalogItem):
    required_competencies: list[CatalogItem]
