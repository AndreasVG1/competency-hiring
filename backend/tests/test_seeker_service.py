from fastapi import HTTPException

from app.db.models import CompetencyLevel, JobSeekerCompetency, User, UserRole
from app.modules.seeker import service


def create_user(db_session, *, email: str) -> User:
    user = User(
        email=email,
        password_hash="hashed",
        role=UserRole.JOB_SEEKER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_profile_upsert_create_path(db_session, monkeypatch):
    user = create_user(db_session, email="service-profile-create@example.com")
    monkeypatch.setattr(
        service,
        "get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": "Occupation"},
    )

    profile = service.upsert_profile(
        db_session,
        user_id=user.id,
        full_name="Alice Example",
        summary="Summary",
        location="Tallinn",
        occupation_key="occ_1",
    )

    assert profile.user_id == user.id
    assert profile.full_name == "Alice Example"
    assert profile.occupation_key == "occ_1"


def test_profile_upsert_update_path(db_session, monkeypatch):
    user = create_user(db_session, email="service-profile-update@example.com")
    monkeypatch.setattr(
        service,
        "get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": "Occupation"},
    )

    created = service.upsert_profile(
        db_session,
        user_id=user.id,
        full_name="Original",
        summary="Old",
        location="Tartu",
        occupation_key="occ_1",
    )
    updated = service.upsert_profile(
        db_session,
        user_id=user.id,
        full_name="Updated",
        summary="New",
        location="Tallinn",
        occupation_key="occ_2",
    )

    assert created.user_id == updated.user_id
    assert updated.full_name == "Updated"
    assert updated.summary == "New"
    assert updated.location == "Tallinn"
    assert updated.occupation_key == "occ_2"


def test_occupation_key_validation_behavior(db_session, monkeypatch):
    user = create_user(db_session, email="service-profile-invalid-occ@example.com")

    def raise_not_found(*_args, **_kwargs):
        raise HTTPException(status_code=404, detail="Occupation not found.")

    monkeypatch.setattr(service, "get_occupation_detail", raise_not_found)

    try:
        service.upsert_profile(
            db_session,
            user_id=user.id,
            full_name="Alice",
            summary=None,
            location=None,
            occupation_key="unknown",
        )
        assert False, "Expected HTTPException for unknown occupation key"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Occupation not found."


def test_competency_key_validation_behavior(db_session, monkeypatch):
    user = create_user(db_session, email="service-comp-invalid-key@example.com")

    def raise_not_found(*_args, **_kwargs):
        raise HTTPException(status_code=404, detail="Competency not found.")

    monkeypatch.setattr(service, "get_competency_detail", raise_not_found)

    try:
        service.add_competency_for_user(
            db_session,
            user_id=user.id,
            competency_key="unknown",
            level=CompetencyLevel.BEGINNER,
        )
        assert False, "Expected HTTPException for unknown competency key"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Competency not found."


def test_duplicate_competency_conflict_path(db_session, monkeypatch):
    user = create_user(db_session, email="service-comp-duplicate@example.com")
    monkeypatch.setattr(
        service,
        "get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency"},
    )

    first = service.add_competency_for_user(
        db_session,
        user_id=user.id,
        competency_key="comp_1",
        level=CompetencyLevel.BEGINNER,
    )
    assert first.id

    try:
        service.add_competency_for_user(
            db_session,
            user_id=user.id,
            competency_key="comp_1",
            level=CompetencyLevel.ADVANCED,
        )
        assert False, "Expected conflict for duplicate competency"
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "Competency already exists for this seeker."


def test_ownership_safe_update_and_delete_behavior(db_session):
    owner = create_user(db_session, email="service-comp-owner@example.com")
    other = create_user(db_session, email="service-comp-other@example.com")

    competency = JobSeekerCompetency(
        user_id=owner.id,
        competency_key="comp_1",
        level=CompetencyLevel.INTERMEDIATE,
    )
    db_session.add(competency)
    db_session.commit()
    db_session.refresh(competency)

    updated = service.update_competency_level_for_user(
        db_session,
        user_id=owner.id,
        competency_id=competency.id,
        level=CompetencyLevel.ADVANCED,
    )
    assert updated.level == CompetencyLevel.ADVANCED

    try:
        service.update_competency_level_for_user(
            db_session,
            user_id=other.id,
            competency_id=competency.id,
            level=CompetencyLevel.BEGINNER,
        )
        assert False, "Expected not found for non-owned competency update"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Seeker competency not found."

    service.delete_competency_for_user(
        db_session,
        user_id=owner.id,
        competency_id=competency.id,
    )
    still_exists = (
        db_session.query(JobSeekerCompetency)
        .filter(JobSeekerCompetency.id == competency.id)
        .one_or_none()
    )
    assert still_exists is None

    try:
        service.delete_competency_for_user(
            db_session,
            user_id=other.id,
            competency_id=competency.id,
        )
        assert False, "Expected not found for missing/non-owned competency delete"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Seeker competency not found."
