from datetime import datetime

from fastapi import HTTPException

from app.db.models import (
    Application,
    CompetencyLevel,
    JobSeekerCompetency,
    JobOffer,
    JobOfferRequirement,
    JobOfferStatus,
    RecruiterProfile,
    RequirementPriority,
    User,
    UserRole,
)
from app.modules.matching.engine import calculate_exact_match_result
from app.modules.matching.schemas import MatchingRequirementInput, SeekerCompetencyInput
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


def test_profile_delete_removes_profile_and_competencies(db_session, monkeypatch):
    user = create_user(db_session, email="service-profile-delete@example.com")
    monkeypatch.setattr(
        service,
        "get_occupation_detail",
        lambda *, occupation_key: {"key": occupation_key, "label": "Occupation"},
    )
    monkeypatch.setattr(
        service,
        "get_competency_detail",
        lambda *, competency_key: {"key": competency_key, "label": "Competency"},
    )

    service.upsert_profile(
        db_session,
        user_id=user.id,
        full_name="Alice Example",
        summary="Summary",
        location="Tallinn",
        occupation_key="occ_1",
    )
    service.add_competency_for_user(
        db_session,
        user_id=user.id,
        competency_key="comp_1",
        level=CompetencyLevel.BEGINNER,
    )

    service.delete_profile_for_user(db_session, user_id=user.id)

    assert service.get_profile_for_user(db_session, user_id=user.id) is None
    assert service.list_competencies_for_user(db_session, user_id=user.id) == []


def test_profile_delete_returns_404_when_profile_missing(db_session):
    user = create_user(db_session, email="service-profile-delete-missing@example.com")

    try:
        service.delete_profile_for_user(db_session, user_id=user.id)
        assert False, "Expected not found for missing seeker profile delete"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Seeker profile not found."


def create_recruiter_user(db_session, *, email: str) -> User:
    user = User(
        email=email,
        password_hash="hashed",
        role=UserRole.RECRUITER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_list_published_job_offers_returns_only_published_with_filters(db_session):
    recruiter = create_recruiter_user(db_session, email="service-marketplace-list-recruiter@example.com")
    seeker = create_user(db_session, email="service-marketplace-list-seeker@example.com")
    db_session.add(
        RecruiterProfile(
            user_id=recruiter.id,
            company_name="Acme",
            contact_name="Alice Recruiter",
        )
    )

    published_backend = JobOffer(
        recruiter_user_id=recruiter.id,
        title="Backend Engineer",
        occupation_key="backend_engineer",
        description="Build Python APIs",
        status=JobOfferStatus.PUBLISHED,
    )
    published_frontend = JobOffer(
        recruiter_user_id=recruiter.id,
        title="Frontend Engineer",
        occupation_key="frontend_engineer",
        description="Build Vue interfaces",
        status=JobOfferStatus.PUBLISHED,
    )
    draft = JobOffer(
        recruiter_user_id=recruiter.id,
        title="Data Analyst",
        occupation_key="data_analyst",
        description="Draft only",
        status=JobOfferStatus.DRAFT,
    )
    db_session.add_all([published_backend, published_frontend, draft])
    db_session.commit()
    applied_application = Application(
        job_offer_id=published_backend.id,
        seeker_user_id=seeker.id,
        consent_given_at=datetime(2026, 4, 1, 10, 0, 0),
    )
    db_session.add(applied_application)
    db_session.commit()

    listed = service.list_published_job_offers(
        db_session,
        seeker_user_id=seeker.id,
        query=None,
        occupation_key=None,
        applied=None,
        limit=20,
        offset=0,
    )
    listed_ids = {item.id for item in listed}
    assert listed_ids == {published_backend.id, published_frontend.id}
    listed_by_id = {item.id: item for item in listed}
    assert listed_by_id[published_backend.id].applied is True
    assert listed_by_id[published_backend.id].application_id == applied_application.id
    assert listed_by_id[published_frontend.id].applied is False
    assert listed_by_id[published_frontend.id].application_id is None

    filtered_query = service.list_published_job_offers(
        db_session,
        seeker_user_id=seeker.id,
        query="python",
        occupation_key=None,
        applied=None,
        limit=20,
        offset=0,
    )
    assert len(filtered_query) == 1
    assert filtered_query[0].id == published_backend.id
    assert filtered_query[0].applied is True

    filtered_occupation = service.list_published_job_offers(
        db_session,
        seeker_user_id=seeker.id,
        query=None,
        occupation_key="frontend_engineer",
        applied=None,
        limit=20,
        offset=0,
    )
    assert len(filtered_occupation) == 1
    assert filtered_occupation[0].id == published_frontend.id
    assert filtered_occupation[0].applied is False

    paged = service.list_published_job_offers(
        db_session,
        seeker_user_id=seeker.id,
        query=None,
        occupation_key=None,
        applied=None,
        limit=1,
        offset=1,
    )
    assert len(paged) == 1


def test_list_published_job_offers_filters_by_applied_state(db_session):
    recruiter = create_recruiter_user(db_session, email="service-marketplace-applied-filter-recruiter@example.com")
    seeker = create_user(db_session, email="service-marketplace-applied-filter-seeker@example.com")
    db_session.add(
        RecruiterProfile(
            user_id=recruiter.id,
            company_name="Acme",
            contact_name="Alice Recruiter",
        )
    )

    applied_offer = JobOffer(
        recruiter_user_id=recruiter.id,
        title="Applied Offer",
        occupation_key="applied_offer",
        description="Applied description",
        status=JobOfferStatus.PUBLISHED,
    )
    not_applied_offer = JobOffer(
        recruiter_user_id=recruiter.id,
        title="Not Applied Offer",
        occupation_key="not_applied_offer",
        description="Not applied description",
        status=JobOfferStatus.PUBLISHED,
    )
    db_session.add_all([applied_offer, not_applied_offer])
    db_session.commit()

    db_session.add(
        Application(
            job_offer_id=applied_offer.id,
            seeker_user_id=seeker.id,
            consent_given_at=datetime(2026, 4, 1, 10, 0, 0),
        )
    )
    db_session.commit()

    applied_items = service.list_published_job_offers(
        db_session,
        seeker_user_id=seeker.id,
        query=None,
        occupation_key=None,
        applied=True,
        limit=20,
        offset=0,
    )
    assert len(applied_items) == 1
    assert applied_items[0].id == applied_offer.id
    assert applied_items[0].applied is True
    assert applied_items[0].application_id is not None

    not_applied_items = service.list_published_job_offers(
        db_session,
        seeker_user_id=seeker.id,
        query=None,
        occupation_key=None,
        applied=False,
        limit=20,
        offset=0,
    )
    assert len(not_applied_items) == 1
    assert not_applied_items[0].id == not_applied_offer.id
    assert not_applied_items[0].applied is False
    assert not_applied_items[0].application_id is None


def test_get_published_job_offer_detail_returns_requirements(db_session, monkeypatch):
    recruiter = create_recruiter_user(db_session, email="service-marketplace-detail-recruiter@example.com")
    seeker = create_user(db_session, email="service-marketplace-detail-seeker@example.com")
    db_session.add(
        RecruiterProfile(
            user_id=recruiter.id,
            company_name="Acme",
            contact_name="Alice Recruiter",
        )
    )
    offer = JobOffer(
        recruiter_user_id=recruiter.id,
        title="Backend Engineer",
        occupation_key="backend_engineer",
        description="Build APIs",
        status=JobOfferStatus.PUBLISHED,
    )
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)

    db_session.add(
        JobOfferRequirement(
            job_offer_id=offer.id,
            competency_key="python",
            priority=RequirementPriority.MUST_HAVE,
        )
    )
    db_session.commit()
    application = Application(
        job_offer_id=offer.id,
        seeker_user_id=seeker.id,
        consent_given_at=datetime(2026, 4, 1, 10, 0, 0),
    )
    db_session.add(application)
    db_session.commit()

    monkeypatch.setattr(
        service,
        "resolve_catalog_competencies",
        lambda *, keys: {
            "items": [{"key": "python", "label": "Python", "activity_indicator_count": 4}],
            "missing_keys": [],
        },
    )

    detail = service.get_published_job_offer_detail_or_404(
        db_session,
        seeker_user_id=seeker.id,
        job_offer_id=offer.id,
    )

    assert detail.id == offer.id
    assert detail.company_name == "Acme"
    assert detail.requirements[0].competency_key == "python"
    assert detail.requirements[0].priority == RequirementPriority.MUST_HAVE
    assert detail.requirements[0].competency_label == "Python"
    assert detail.requirements[0].activity_indicator_count == 4
    assert detail.applied is True
    assert detail.application_id == application.id


def test_get_published_job_offer_detail_returns_404_for_non_published_or_missing(db_session):
    recruiter = create_recruiter_user(db_session, email="service-marketplace-404-recruiter@example.com")
    seeker = create_user(db_session, email="service-marketplace-404-seeker@example.com")
    offer = JobOffer(
        recruiter_user_id=recruiter.id,
        title="Backend Engineer",
        occupation_key="backend_engineer",
        description="Draft offer",
        status=JobOfferStatus.DRAFT,
    )
    db_session.add(offer)
    db_session.commit()

    try:
        service.get_published_job_offer_detail_or_404(
            db_session,
            seeker_user_id=seeker.id,
            job_offer_id=offer.id,
        )
        assert False, "Expected 404 for non-published offer"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Published job offer not found."

    try:
        service.get_published_job_offer_detail_or_404(
            db_session,
            seeker_user_id=seeker.id,
            job_offer_id=999999,
        )
        assert False, "Expected 404 for missing offer"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Published job offer not found."


def test_private_job_offer_analysis_with_explanation_wraps_matching_result(db_session):
    matching_payload = calculate_exact_match_result(
        job_offer_id=777,
        seeker_user_id=55,
        requirements=[
            MatchingRequirementInput(
                competency_key="comp_api",
                priority=RequirementPriority.MUST_HAVE,
            ),
            MatchingRequirementInput(
                competency_key="comp_sql",
                priority=RequirementPriority.IMPORTANT,
            ),
        ],
        seeker_competencies=[
            SeekerCompetencyInput(
                competency_key="comp_api",
                level=CompetencyLevel.INTERMEDIATE,
            ),
        ],
    )

    def _stub_matching(*_args, **_kwargs):
        return matching_payload

    original_matching = service.get_private_matching_analysis_for_seeker
    service.get_private_matching_analysis_for_seeker = _stub_matching
    try:
        result = service.get_private_job_offer_analysis_with_explanation(
            db_session,
            seeker_user_id=55,
            job_offer_id=777,
        )
    finally:
        service.get_private_matching_analysis_for_seeker = original_matching

    assert result.job_offer_id == 777
    assert result.seeker_user_id == 55
    assert result.algorithm_version == "v2_exact_priority_level_dual_signal"
    assert result.explanation.audience == "seeker"
    assert result.explanation.summary.decision_support_notice == (
        "This analysis supports your decision and does not make hiring decisions."
    )
    assert result.explanation.development_roadmap is not None


def test_private_job_offer_analysis_with_explanation_propagates_matching_http_errors(db_session):
    def _raise_matching_http_error(*_args, **_kwargs):
        raise HTTPException(status_code=404, detail="Published job offer not found.")

    original_matching = service.get_private_matching_analysis_for_seeker
    service.get_private_matching_analysis_for_seeker = _raise_matching_http_error
    try:
        try:
            service.get_private_job_offer_analysis_with_explanation(
                db_session,
                seeker_user_id=66,
                job_offer_id=888,
            )
            assert False, "Expected matching HTTPException to propagate"
        except HTTPException as exc:
            assert exc.status_code == 404
            assert exc.detail == "Published job offer not found."
    finally:
        service.get_private_matching_analysis_for_seeker = original_matching


def test_private_job_offer_analysis_with_explanation_uses_fallback_for_unknown_algorithm(
    db_session,
):
    payload = calculate_exact_match_result(
        job_offer_id=999,
        seeker_user_id=77,
        requirements=[
            MatchingRequirementInput(
                competency_key="comp_api",
                priority=RequirementPriority.MUST_HAVE,
            ),
        ],
        seeker_competencies=[],
    ).model_copy(update={"algorithm_version": "v999_unknown_algorithm"})

    def _stub_matching(*_args, **_kwargs):
        return payload

    original_matching = service.get_private_matching_analysis_for_seeker
    service.get_private_matching_analysis_for_seeker = _stub_matching
    try:
        result = service.get_private_job_offer_analysis_with_explanation(
            db_session,
            seeker_user_id=77,
            job_offer_id=999,
        )
    finally:
        service.get_private_matching_analysis_for_seeker = original_matching

    assert result.explanation.audience == "seeker"
    assert result.explanation.algorithm_version == "v999_unknown_algorithm"
    assert result.explanation.highlights == []
    assert result.explanation.gaps == []
    assert result.explanation.development_roadmap == []
    assert "Detailed explanation templates are unavailable" in result.explanation.transparency_notes[-1]
