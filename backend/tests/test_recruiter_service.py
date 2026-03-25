from fastapi import HTTPException

from app.db.models import (
    JobOffer,
    JobOfferRequirement,
    JobOfferStatus,
    RequirementPriority,
    User,
    UserRole,
)
from app.modules.recruiter import service


def create_user(db_session, *, email: str) -> User:
    user = User(
        email=email,
        password_hash="hashed",
        role=UserRole.RECRUITER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_profile_upsert_create_path(db_session):
    user = create_user(db_session, email="service-recruiter-profile-create@example.com")

    profile = service.upsert_profile(
        db_session,
        user_id=user.id,
        company_name="Acme",
        contact_name="Alice",
    )

    assert profile.user_id == user.id
    assert profile.company_name == "Acme"
    assert profile.contact_name == "Alice"


def test_profile_upsert_update_path(db_session):
    user = create_user(db_session, email="service-recruiter-profile-update@example.com")

    created = service.upsert_profile(
        db_session,
        user_id=user.id,
        company_name="Acme",
        contact_name="Alice",
    )
    updated = service.upsert_profile(
        db_session,
        user_id=user.id,
        company_name="Beta",
        contact_name="Bob",
    )

    assert created.user_id == updated.user_id
    assert updated.company_name == "Beta"
    assert updated.contact_name == "Bob"


def test_job_offer_create_list_get_and_update_owned_path_behavior(db_session):
    user = create_user(db_session, email="service-recruiter-offer-owned@example.com")

    created = service.create_job_offer_for_user(
        db_session,
        user_id=user.id,
        title="Backend Engineer",
        description="Build APIs",
    )
    assert created.status == JobOfferStatus.DRAFT

    offers = service.list_job_offers_for_user(db_session, user_id=user.id)
    assert len(offers) == 1
    assert offers[0].id == created.id

    fetched = service.get_owned_job_offer_or_404(
        db_session,
        user_id=user.id,
        job_offer_id=created.id,
    )
    assert fetched.id == created.id

    updated = service.update_job_offer_for_user(
        db_session,
        user_id=user.id,
        job_offer_id=created.id,
        title="Senior Backend Engineer",
        description="Build and improve APIs",
    )
    assert updated.title == "Senior Backend Engineer"
    assert updated.description == "Build and improve APIs"
    assert updated.status == JobOfferStatus.DRAFT


def test_requirement_competency_key_validation_behavior(db_session, monkeypatch):
    user = create_user(db_session, email="service-recruiter-req-invalid-key@example.com")
    offer = service.create_job_offer_for_user(
        db_session,
        user_id=user.id,
        title="Backend Engineer",
        description="Build APIs",
    )

    def raise_not_found(*_args, **_kwargs):
        raise HTTPException(status_code=404, detail="Competency not found.")

    monkeypatch.setattr(service, "get_competency_detail", raise_not_found)

    try:
        service.add_requirement_to_job_offer(
            db_session,
            user_id=user.id,
            job_offer_id=offer.id,
            competency_key="unknown",
            priority=RequirementPriority.MUST_HAVE,
        )
        assert False, "Expected HTTPException for unknown competency key"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Competency not found."


def test_duplicate_requirement_conflict_behavior(db_session, monkeypatch):
    user = create_user(db_session, email="service-recruiter-req-duplicate@example.com")
    offer = service.create_job_offer_for_user(
        db_session,
        user_id=user.id,
        title="Backend Engineer",
        description="Build APIs",
    )

    monkeypatch.setattr(
        service,
        "get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency"},
    )

    first = service.add_requirement_to_job_offer(
        db_session,
        user_id=user.id,
        job_offer_id=offer.id,
        competency_key="comp_1",
        priority=RequirementPriority.MUST_HAVE,
    )
    assert first.id

    try:
        service.add_requirement_to_job_offer(
            db_session,
            user_id=user.id,
            job_offer_id=offer.id,
            competency_key="comp_1",
            priority=RequirementPriority.IMPORTANT,
        )
        assert False, "Expected conflict for duplicate requirement"
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "Requirement already exists for this job offer."


def test_ownership_safe_requirement_update_and_delete_behavior(db_session):
    owner = create_user(db_session, email="service-recruiter-req-owner@example.com")
    other = create_user(db_session, email="service-recruiter-req-other@example.com")

    offer = JobOffer(
        recruiter_user_id=owner.id,
        title="Backend Engineer",
        description="Build APIs",
        status=JobOfferStatus.DRAFT,
    )
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)

    requirement = JobOfferRequirement(
        job_offer_id=offer.id,
        competency_key="comp_1",
        priority=RequirementPriority.IMPORTANT,
    )
    db_session.add(requirement)
    db_session.commit()
    db_session.refresh(requirement)

    updated = service.update_requirement_priority(
        db_session,
        user_id=owner.id,
        job_offer_id=offer.id,
        requirement_id=requirement.id,
        priority=RequirementPriority.NICE_TO_HAVE,
    )
    assert updated.priority == RequirementPriority.NICE_TO_HAVE

    try:
        service.update_requirement_priority(
            db_session,
            user_id=other.id,
            job_offer_id=offer.id,
            requirement_id=requirement.id,
            priority=RequirementPriority.MUST_HAVE,
        )
        assert False, "Expected not found for non-owned requirement update"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Job offer not found."

    service.delete_requirement(
        db_session,
        user_id=owner.id,
        job_offer_id=offer.id,
        requirement_id=requirement.id,
    )
    still_exists = (
        db_session.query(JobOfferRequirement)
        .filter(JobOfferRequirement.id == requirement.id)
        .one_or_none()
    )
    assert still_exists is None

    try:
        service.delete_requirement(
            db_session,
            user_id=other.id,
            job_offer_id=offer.id,
            requirement_id=requirement.id,
        )
        assert False, "Expected not found for missing/non-owned requirement delete"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Job offer not found."
