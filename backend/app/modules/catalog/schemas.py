from pydantic import BaseModel, Field


class CatalogItem(BaseModel):
    key: str
    label: str


class CompetencyCatalogItem(CatalogItem):
    code: str
    ekr_level: int | None = None


class ActivityIndicatorCatalogItem(BaseModel):
    key: str
    text: str
    code: str


class CompetencyCatalogDetail(CompetencyCatalogItem):
    activity_indicators: list[ActivityIndicatorCatalogItem] = Field(default_factory=list)


class OccupationDetail(CatalogItem):
    required_competencies: list[CatalogItem]
