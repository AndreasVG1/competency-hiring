from fastapi import HTTPException, status

from app.modules.catalog import repository

COMPETENCY_NOT_FOUND_MESSAGE = "Competency not found."
OCCUPATION_NOT_FOUND_MESSAGE = "Occupation not found."


def _to_catalog_item(*, key: str, label: str) -> dict:
    return {
        "key": key,
        "label": label,
    }


def search_competencies(*, query: str, limit: int) -> list[dict]:
    rows = repository.search_competencies(query=query.strip(), limit=limit)

    return [
        {
            "key": row["id"],
            "label": row["name"],
            "code": row["code"],
            "ekr_level": row.get("ekr_level"),
        }
        for row in rows
    ]


def get_competency_detail(*, competency_key: str) -> dict:
    row = repository.get_competency_by_key(competency_key=competency_key)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=COMPETENCY_NOT_FOUND_MESSAGE,
        )

    activity_indicators = [
        {
            "key": item["id"],
            "text": item["text"],
            "code": item["code"],
        }
        for item in row.get("activity_indicators", [])
    ]

    return {
        "key": row["id"],
        "label": row["name"],
        "code": row["code"],
        "ekr_level": row.get("ekr_level"),
        "activity_indicators": activity_indicators,
    }


def search_occupations(*, query: str, limit: int) -> list[dict]:
    rows = repository.search_occupations(query=query.strip(), limit=limit)
    return [_to_catalog_item(key=row["id"], label=row["name"]) for row in rows]


def get_occupation_detail(*, occupation_key: str) -> dict:
    row = repository.get_occupation_by_key(occupation_key=occupation_key)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=OCCUPATION_NOT_FOUND_MESSAGE,
        )

    required_competencies = [
        _to_catalog_item(key=item["id"], label=item["name"])
        for item in row.get("required_competencies", [])
    ]

    return {
        "key": row["id"],
        "label": row["name"],
        "required_competencies": required_competencies,
    }
