from datetime import datetime, timezone

from fastapi import HTTPException
import pytest
from sqlalchemy import text

from app.db.models import (
    Application,
    ApplicationMatchingSnapshot,
    ApplicationSnapshot,
    CompetencyLevel,
    JobOffer,
    JobOfferRequirement,
    JobOfferStatus,
    JobSeekerCompetency,
    JobSeekerProfile,
    RequirementPriority,
    User,
    UserRole,
)
from app.modules.applications import service
from app.modules.matching.engine import MatchingInputValidationError


def _enable_sqlite_foreign_keys(db_session) -> None:
    db_session.execute(text("PRAGMA foreign_keys = ON"))


def _create_user(db_session, *, email: str, role: UserRole) -> User:
    user = User(email=email, password_hash="hashed", role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_offer(
    db_session,
    *,
    recruiter_user_id: int,
    offer_status: JobOfferStatus,
) -> JobOffer:
    offer = JobOffer(
        recruiter_user_id=recruiter_user_id,
        title="Backend Engineer",
        occupation_key="backend_engineer",
        description="Build APIs",
        status=offer_status,
    )
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)
    return offer


def _create_profile(db_session, *, seeker_user_id: int) -> JobSeekerProfile:
    profile = JobSeekerProfile(
        user_id=seeker_user_id,
        full_name="Alice Example",
        summary="Summary",
        location="Tallinn",
        occupation_key="backend_engineer",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def _add_competency(
    db_session,
    *,
    seeker_user_id: int,
    competency_key: str,
    level: CompetencyLevel,
) -> JobSeekerCompetency:
    item = JobSeekerCompetency(
        user_id=seeker_user_id,
        competency_key=competency_key,
        level=level,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def _add_requirement(
    db_session,
    *,
    job_offer_id: int,
    competency_key: str,
    priority: RequirementPriority,
) -> JobOfferRequirement:
    item = JobOfferRequirement(
        job_offer_id=job_offer_id,
        competency_key=competency_key,
        priority=priority,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_apply_requires_job_seeker_role(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session,
        email="application-service-role-recruiter@example.com",
        role=UserRole.RECRUITER,
    )

    try:
        service.apply_to_published_job_offer(
            db_session,
            seeker_user=recruiter,
            job_offer_id=1,
        )
        assert False, "Expected forbidden for non-seeker apply."
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Only job seekers can apply to job offers."


@pytest.mark.parametrize("offer_status", [JobOfferStatus.DRAFT, JobOfferStatus.ARCHIVED])
def test_apply_rejects_non_published_offer_status(db_session, offer_status: JobOfferStatus):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session,
        email=f"application-service-offer-recruiter-{offer_status.value}@example.com",
        role=UserRole.RECRUITER,
    )
    seeker = _create_user(
        db_session,
        email=f"application-service-offer-seeker-{offer_status.value}@example.com",
        role=UserRole.JOB_SEEKER,
    )
    offer = _create_offer(
        db_session,
        recruiter_user_id=recruiter.id,
        offer_status=offer_status,
    )
    _create_profile(db_session, seeker_user_id=seeker.id)

    try:
        service.apply_to_published_job_offer(
            db_session,
            seeker_user=seeker,
            job_offer_id=offer.id,
        )
        assert False, "Expected not found for non-published offer."
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Published job offer not found."


def test_apply_requires_existing_seeker_profile(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session,
        email="application-service-profile-recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    seeker = _create_user(
        db_session,
        email="application-service-profile-seeker@example.com",
        role=UserRole.JOB_SEEKER,
    )
    offer = _create_offer(
        db_session,
        recruiter_user_id=recruiter.id,
        offer_status=JobOfferStatus.PUBLISHED,
    )

    try:
        service.apply_to_published_job_offer(
            db_session,
            seeker_user=seeker,
            job_offer_id=offer.id,
        )
        assert False, "Expected not found when seeker profile is missing."
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Seeker profile not found."


def test_apply_rejects_duplicate_application(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session,
        email="application-service-duplicate-recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    seeker = _create_user(
        db_session,
        email="application-service-duplicate-seeker@example.com",
        role=UserRole.JOB_SEEKER,
    )
    offer = _create_offer(
        db_session,
        recruiter_user_id=recruiter.id,
        offer_status=JobOfferStatus.PUBLISHED,
    )
    _create_profile(db_session, seeker_user_id=seeker.id)
    _add_competency(
        db_session,
        seeker_user_id=seeker.id,
        competency_key="comp_1",
        level=CompetencyLevel.BEGINNER,
    )

    first = service.apply_to_published_job_offer(
        db_session,
        seeker_user=seeker,
        job_offer_id=offer.id,
    )
    assert first.id
    matching_snapshot_count_before = (
        db_session.query(ApplicationMatchingSnapshot)
        .join(Application, Application.id == ApplicationMatchingSnapshot.application_id)
        .filter(
            Application.job_offer_id == offer.id,
            Application.seeker_user_id == seeker.id,
        )
        .count()
    )
    assert matching_snapshot_count_before == 1

    try:
        service.apply_to_published_job_offer(
            db_session,
            seeker_user=seeker,
            job_offer_id=offer.id,
        )
        assert False, "Expected conflict for duplicate apply."
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "Application already exists for this seeker and job offer."

    matching_snapshot_count_after = (
        db_session.query(ApplicationMatchingSnapshot)
        .join(Application, Application.id == ApplicationMatchingSnapshot.application_id)
        .filter(
            Application.job_offer_id == offer.id,
            Application.seeker_user_id == seeker.id,
        )
        .count()
    )
    assert matching_snapshot_count_after == 1


def test_apply_persists_application_with_snapshot_and_consent_time(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session,
        email="application-service-success-recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    seeker = _create_user(
        db_session,
        email="application-service-success-seeker@example.com",
        role=UserRole.JOB_SEEKER,
    )
    offer = _create_offer(
        db_session,
        recruiter_user_id=recruiter.id,
        offer_status=JobOfferStatus.PUBLISHED,
    )
    _create_profile(db_session, seeker_user_id=seeker.id)
    _add_competency(
        db_session,
        seeker_user_id=seeker.id,
        competency_key="comp_a",
        level=CompetencyLevel.ADVANCED,
    )
    _add_competency(
        db_session,
        seeker_user_id=seeker.id,
        competency_key="comp_b",
        level=CompetencyLevel.INTERMEDIATE,
    )
    _add_requirement(
        db_session,
        job_offer_id=offer.id,
        competency_key="comp_a",
        priority=RequirementPriority.MUST_HAVE,
    )

    consent_time = datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
    created = service.apply_to_published_job_offer(
        db_session,
        seeker_user=seeker,
        job_offer_id=offer.id,
        consent_given_at=consent_time,
    )

    db_session.refresh(created)
    persisted = (
        db_session.query(Application)
        .filter(Application.id == created.id)
        .one()
    )
    snapshot = (
        db_session.query(ApplicationSnapshot)
        .filter(ApplicationSnapshot.application_id == created.id)
        .one()
    )
    matching_snapshot = (
        db_session.query(ApplicationMatchingSnapshot)
        .filter(ApplicationMatchingSnapshot.application_id == created.id)
        .one()
    )

    assert persisted.seeker_user_id == seeker.id
    assert persisted.job_offer_id == offer.id
    assert persisted.consent_given_at == consent_time.replace(tzinfo=None)
    assert persisted.created_at is not None

    assert snapshot.full_name == "Alice Example"
    assert snapshot.summary == "Summary"
    assert snapshot.location == "Tallinn"
    assert snapshot.occupation_key == "backend_engineer"
    assert snapshot.competencies == [
        {"competency_key": "comp_a", "level": "advanced"},
        {"competency_key": "comp_b", "level": "intermediate"},
    ]
    assert snapshot.audit_metadata == {
        "job_offer_id": str(offer.id),
        "job_offer_title": "Backend Engineer",
        "job_offer_occupation_key": "backend_engineer",
    }
    assert matching_snapshot.algorithm_version == "v2_exact_priority_level_dual_signal"
    assert isinstance(matching_snapshot.score, float)
    assert matching_snapshot.score == 100.0
    assert matching_snapshot.result_payload["scope"] == "shared_application_snapshot"
    assert matching_snapshot.result_payload["algorithm_version"] == matching_snapshot.algorithm_version
    assert matching_snapshot.result_payload["score"] == matching_snapshot.score


def test_apply_rolls_back_and_returns_422_for_matching_input_validation_error(
    db_session,
    monkeypatch,
):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session,
        email="application-service-matching-validation-recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    seeker = _create_user(
        db_session,
        email="application-service-matching-validation-seeker@example.com",
        role=UserRole.JOB_SEEKER,
    )
    offer = _create_offer(
        db_session,
        recruiter_user_id=recruiter.id,
        offer_status=JobOfferStatus.PUBLISHED,
    )
    _create_profile(db_session, seeker_user_id=seeker.id)

    def _raise_matching_validation_error(*_args, **_kwargs):
        raise MatchingInputValidationError(
            code="duplicate_requirement_competency_key",
            message="Duplicate requirement competency_key: 'comp_api'.",
        )

    monkeypatch.setattr(
        service,
        "calculate_matching_for_job_offer_and_seeker",
        _raise_matching_validation_error,
    )

    with pytest.raises(HTTPException) as exc_info:
        service.apply_to_published_job_offer(
            db_session,
            seeker_user=seeker,
            job_offer_id=offer.id,
        )

    assert exc_info.value.status_code == 422
    assert (
        exc_info.value.detail
        == "Invalid matching input: duplicate_requirement_competency_key: "
        "Duplicate requirement competency_key: 'comp_api'."
    )
    assert (
        db_session.query(Application)
        .filter(
            Application.job_offer_id == offer.id,
            Application.seeker_user_id == seeker.id,
        )
        .count()
        == 0
    )
    assert db_session.query(ApplicationSnapshot).count() == 0
    assert db_session.query(ApplicationMatchingSnapshot).count() == 0


def test_apply_rolls_back_when_commit_fails(db_session, monkeypatch):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session,
        email="application-service-commit-failure-recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    seeker = _create_user(
        db_session,
        email="application-service-commit-failure-seeker@example.com",
        role=UserRole.JOB_SEEKER,
    )
    offer = _create_offer(
        db_session,
        recruiter_user_id=recruiter.id,
        offer_status=JobOfferStatus.PUBLISHED,
    )
    _create_profile(db_session, seeker_user_id=seeker.id)
    _add_competency(
        db_session,
        seeker_user_id=seeker.id,
        competency_key="comp_a",
        level=CompetencyLevel.INTERMEDIATE,
    )
    _add_requirement(
        db_session,
        job_offer_id=offer.id,
        competency_key="comp_a",
        priority=RequirementPriority.IMPORTANT,
    )

    def _raise_commit_failure():
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(db_session, "commit", _raise_commit_failure)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        service.apply_to_published_job_offer(
            db_session,
            seeker_user=seeker,
            job_offer_id=offer.id,
        )

    assert (
        db_session.query(Application)
        .filter(
            Application.job_offer_id == offer.id,
            Application.seeker_user_id == seeker.id,
        )
        .count()
        == 0
    )
    assert db_session.query(ApplicationSnapshot).count() == 0
    assert db_session.query(ApplicationMatchingSnapshot).count() == 0


def test_list_applications_for_seeker_returns_only_own_rows(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session,
        email="application-service-list-recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    seeker_one = _create_user(
        db_session,
        email="application-service-list-seeker-1@example.com",
        role=UserRole.JOB_SEEKER,
    )
    seeker_two = _create_user(
        db_session,
        email="application-service-list-seeker-2@example.com",
        role=UserRole.JOB_SEEKER,
    )

    offer_one = _create_offer(
        db_session,
        recruiter_user_id=recruiter.id,
        offer_status=JobOfferStatus.PUBLISHED,
    )
    offer_two = _create_offer(
        db_session,
        recruiter_user_id=recruiter.id,
        offer_status=JobOfferStatus.PUBLISHED,
    )
    _create_profile(db_session, seeker_user_id=seeker_one.id)
    _create_profile(db_session, seeker_user_id=seeker_two.id)

    service.apply_to_published_job_offer(
        db_session,
        seeker_user=seeker_one,
        job_offer_id=offer_one.id,
    )
    service.apply_to_published_job_offer(
        db_session,
        seeker_user=seeker_two,
        job_offer_id=offer_one.id,
    )
    created_latest = service.apply_to_published_job_offer(
        db_session,
        seeker_user=seeker_one,
        job_offer_id=offer_two.id,
    )

    listed = service.list_applications_for_seeker(
        db_session,
        seeker_user_id=seeker_one.id,
    )
    assert len(listed) == 2
    assert all(item.seeker_user_id == seeker_one.id for item in listed)
    assert listed[0].id == created_latest.id


def test_list_applicants_for_owned_job_offer_returns_snapshot_only(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session,
        email="application-service-applicants-recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    seeker = _create_user(
        db_session,
        email="application-service-applicants-seeker@example.com",
        role=UserRole.JOB_SEEKER,
    )
    offer = _create_offer(
        db_session,
        recruiter_user_id=recruiter.id,
        offer_status=JobOfferStatus.PUBLISHED,
    )
    profile = _create_profile(db_session, seeker_user_id=seeker.id)

    created = service.apply_to_published_job_offer(
        db_session,
        seeker_user=seeker,
        job_offer_id=offer.id,
    )

    profile.full_name = "Changed Later"
    db_session.commit()

    listed = service.list_applicants_for_owned_job_offer(
        db_session,
        recruiter_user_id=recruiter.id,
        job_offer_id=offer.id,
    )
    assert len(listed) == 1
    item = listed[0]
    assert item["application_id"] == created.id
    assert item["seeker_user_id"] == seeker.id
    assert item["shared_profile"]["full_name"] == "Alice Example"
    assert item["shared_matching"] is not None
    assert item["shared_matching"]["algorithm_version"] == "v2_exact_priority_level_dual_signal"
    assert isinstance(item["shared_matching"]["score"], float)
    assert item["shared_matching"]["result_payload"]["scope"] == "shared_application_snapshot"
    assert item["shared_matching"]["snapshot_created_at"] is not None


def test_list_applicants_for_owned_job_offer_returns_null_shared_matching_when_snapshot_missing(
    db_session,
):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session,
        email="application-service-applicants-missing-matching-recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    seeker = _create_user(
        db_session,
        email="application-service-applicants-missing-matching-seeker@example.com",
        role=UserRole.JOB_SEEKER,
    )
    offer = _create_offer(
        db_session,
        recruiter_user_id=recruiter.id,
        offer_status=JobOfferStatus.PUBLISHED,
    )
    _create_profile(db_session, seeker_user_id=seeker.id)

    created = service.apply_to_published_job_offer(
        db_session,
        seeker_user=seeker,
        job_offer_id=offer.id,
    )
    (
        db_session.query(ApplicationMatchingSnapshot)
        .filter(ApplicationMatchingSnapshot.application_id == created.id)
        .delete()
    )
    db_session.commit()

    listed = service.list_applicants_for_owned_job_offer(
        db_session,
        recruiter_user_id=recruiter.id,
        job_offer_id=offer.id,
    )
    assert len(listed) == 1
    item = listed[0]
    assert item["application_id"] == created.id
    assert item["shared_matching"] is None


def test_list_applicants_for_owned_job_offer_returns_404_for_non_owned_offer(db_session):
    _enable_sqlite_foreign_keys(db_session)
    owner = _create_user(
        db_session,
        email="application-service-applicants-owner@example.com",
        role=UserRole.RECRUITER,
    )
    other = _create_user(
        db_session,
        email="application-service-applicants-other@example.com",
        role=UserRole.RECRUITER,
    )
    offer = _create_offer(
        db_session,
        recruiter_user_id=owner.id,
        offer_status=JobOfferStatus.PUBLISHED,
    )

    with pytest.raises(HTTPException) as exc_info:
        service.list_applicants_for_owned_job_offer(
            db_session,
            recruiter_user_id=other.id,
            job_offer_id=offer.id,
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Job offer not found."
