from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.db.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.catalog.schemas import (
    CatalogItem,
    CompetencyResolveRequest,
    CompetencyResolveResponse,
    CompetencyCatalogDetail,
    CompetencyCatalogItem,
    OccupationDetail,
)
from app.modules.catalog.service import (
    get_competency_detail,
    get_occupation_detail,
    resolve_competencies,
    search_competencies,
    search_occupations,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])

CurrentUser = Annotated[User, Depends(get_current_user)]
QueryText = Annotated[str, Query(max_length=200)]
SearchLimit = Annotated[int, Query(ge=1, le=100)]


@router.get("/competencies", response_model=list[CompetencyCatalogItem])
def list_competencies(
    _current_user: CurrentUser,
    query: QueryText = "",
    limit: SearchLimit = 20,
) -> list[CompetencyCatalogItem]:
    return [
        CompetencyCatalogItem.model_validate(item)
        for item in search_competencies(query=query, limit=limit)
    ]


@router.post("/competencies/resolve", response_model=CompetencyResolveResponse)
def resolve_competency_batch(
    request: CompetencyResolveRequest,
    _current_user: CurrentUser,
) -> CompetencyResolveResponse:
    return CompetencyResolveResponse.model_validate(
        resolve_competencies(keys=request.keys),
    )


@router.get("/competencies/{competency_key}", response_model=CompetencyCatalogDetail)
def read_competency_detail(
    competency_key: str,
    _current_user: CurrentUser,
) -> CompetencyCatalogDetail:
    return CompetencyCatalogDetail.model_validate(
        get_competency_detail(competency_key=competency_key),
    )


@router.get("/occupations", response_model=list[CatalogItem])
def list_occupations(
    _current_user: CurrentUser,
    query: QueryText = "",
    limit: SearchLimit = 20,
) -> list[CatalogItem]:
    return [
        CatalogItem.model_validate(item)
        for item in search_occupations(query=query, limit=limit)
    ]


@router.get("/occupations/{occupation_key}", response_model=OccupationDetail)
def read_occupation_detail(
    occupation_key: str,
    _current_user: CurrentUser,
) -> OccupationDetail:
    return OccupationDetail.model_validate(
        get_occupation_detail(occupation_key=occupation_key),
    )
