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


class CompetencyResolveRequest(BaseModel):
    keys: list[str] = Field(..., max_length=500)


class ResolvedCompetencyItem(BaseModel):
    key: str
    label: str
    activity_indicator_count: int


class CompetencyResolveResponse(BaseModel):
    items: list[ResolvedCompetencyItem] = Field(default_factory=list)
    missing_keys: list[str] = Field(default_factory=list)
