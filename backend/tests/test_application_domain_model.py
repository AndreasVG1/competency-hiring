from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.models import (
    Application,
    ApplicationMatchingSnapshot,
    ApplicationSnapshot,
    JobOffer,
    JobOfferStatus,
    User,
    UserRole,
)


def _enable_sqlite_foreign_keys(db_session) -> None:
    db_session.execute(text("PRAGMA foreign_keys = ON"))


def _create_user(db_session, *, email: str, role: UserRole) -> User:
    user = User(email=email, password_hash="hashed", role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_job_offer(db_session, *, recruiter_user_id: int) -> JobOffer:
    offer = JobOffer(
        recruiter_user_id=recruiter_user_id,
        title="Backend Engineer",
        occupation_key="backend_engineer",
        description="Build APIs",
        status=JobOfferStatus.PUBLISHED,
    )
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)
    return offer


def _create_application(
    db_session,
    *,
    job_offer_id: int,
    seeker_user_id: int,
) -> Application:
    application = Application(
        job_offer_id=job_offer_id,
        seeker_user_id=seeker_user_id,
        consent_given_at=datetime.now(timezone.utc),
    )
    db_session.add(application)
    db_session.commit()
    db_session.refresh(application)
    return application


def _create_application_matching_snapshot(
    db_session,
    *,
    application_id: int,
    algorithm_version: str = "v2_exact_priority_level_dual_signal",
    score: float = 72.5,
    result_payload: dict[str, object] | None = None,
) -> ApplicationMatchingSnapshot:
    payload = result_payload or {
        "algorithm_version": algorithm_version,
        "scope": "shared_application_snapshot",
        "score": score,
    }
    snapshot = ApplicationMatchingSnapshot(
        application_id=application_id,
        algorithm_version=algorithm_version,
        score=score,
        result_payload=payload,
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    return snapshot


def test_application_unique_constraint_on_job_offer_and_seeker(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session, email="application-model-recruiter-unique@example.com", role=UserRole.RECRUITER
    )
    seeker = _create_user(
        db_session, email="application-model-seeker-unique@example.com", role=UserRole.JOB_SEEKER
    )
    offer = _create_job_offer(db_session, recruiter_user_id=recruiter.id)

    _create_application(
        db_session,
        job_offer_id=offer.id,
        seeker_user_id=seeker.id,
    )

    duplicate = Application(
        job_offer_id=offer.id,
        seeker_user_id=seeker.id,
        consent_given_at=datetime.now(timezone.utc),
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_application_snapshot_requires_existing_application_fk(db_session):
    _enable_sqlite_foreign_keys(db_session)

    snapshot = ApplicationSnapshot(
        application_id=999999,
        full_name="Alice Example",
        summary="Summary",
        location="Tallinn",
        occupation_key="backend_engineer",
        competencies=[{"competency_key": "comp_1", "level": "beginner"}],
        audit_metadata={"job_offer_title": "Backend Engineer"},
    )
    db_session.add(snapshot)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_application_matching_snapshot_requires_existing_application_fk(db_session):
    _enable_sqlite_foreign_keys(db_session)

    matching_snapshot = ApplicationMatchingSnapshot(
        application_id=999999,
        algorithm_version="v2_exact_priority_level_dual_signal",
        score=66.7,
        result_payload={
            "algorithm_version": "v2_exact_priority_level_dual_signal",
            "score": 66.7,
            "scope": "shared_application_snapshot",
        },
    )
    db_session.add(matching_snapshot)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_application_snapshot_is_one_to_one_by_primary_key(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session, email="application-model-recruiter-onetoone@example.com", role=UserRole.RECRUITER
    )
    seeker = _create_user(
        db_session, email="application-model-seeker-onetoone@example.com", role=UserRole.JOB_SEEKER
    )
    offer = _create_job_offer(db_session, recruiter_user_id=recruiter.id)
    application = _create_application(
        db_session,
        job_offer_id=offer.id,
        seeker_user_id=seeker.id,
    )

    first = ApplicationSnapshot(
        application_id=application.id,
        full_name="Alice Example",
        summary="Summary",
        location="Tallinn",
        occupation_key="backend_engineer",
        competencies=[{"competency_key": "comp_1", "level": "beginner"}],
        audit_metadata={"job_offer_title": "Backend Engineer"},
    )
    db_session.add(first)
    db_session.commit()
    db_session.expunge(first)

    second = ApplicationSnapshot(
        application_id=application.id,
        full_name="Alice Example Updated",
        summary="Updated summary",
        location="Tartu",
        occupation_key="backend_engineer",
        competencies=[{"competency_key": "comp_2", "level": "advanced"}],
        audit_metadata={"job_offer_title": "Backend Engineer"},
    )
    db_session.add(second)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_application_matching_snapshot_is_one_to_one_by_primary_key(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session, email="application-model-matching-recruiter-onetoone@example.com", role=UserRole.RECRUITER
    )
    seeker = _create_user(
        db_session, email="application-model-matching-seeker-onetoone@example.com", role=UserRole.JOB_SEEKER
    )
    offer = _create_job_offer(db_session, recruiter_user_id=recruiter.id)
    application = _create_application(
        db_session,
        job_offer_id=offer.id,
        seeker_user_id=seeker.id,
    )

    _create_application_matching_snapshot(
        db_session,
        application_id=application.id,
    )

    duplicate = ApplicationMatchingSnapshot(
        application_id=application.id,
        algorithm_version="v3_future",
        score=80.0,
        result_payload={
            "algorithm_version": "v3_future",
            "scope": "shared_application_snapshot",
            "score": 80.0,
        },
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_deleting_job_offer_cascades_to_applications_and_snapshots(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session, email="application-model-recruiter-cascade-offer@example.com", role=UserRole.RECRUITER
    )
    seeker = _create_user(
        db_session, email="application-model-seeker-cascade-offer@example.com", role=UserRole.JOB_SEEKER
    )
    offer = _create_job_offer(db_session, recruiter_user_id=recruiter.id)
    application = _create_application(
        db_session,
        job_offer_id=offer.id,
        seeker_user_id=seeker.id,
    )
    snapshot = ApplicationSnapshot(
        application_id=application.id,
        full_name="Alice Example",
        summary="Summary",
        location="Tallinn",
        occupation_key="backend_engineer",
        competencies=[{"competency_key": "comp_1", "level": "beginner"}],
        audit_metadata={"job_offer_title": "Backend Engineer"},
    )
    matching_snapshot = ApplicationMatchingSnapshot(
        application_id=application.id,
        algorithm_version="v2_exact_priority_level_dual_signal",
        score=70.0,
        result_payload={
            "algorithm_version": "v2_exact_priority_level_dual_signal",
            "scope": "shared_application_snapshot",
            "score": 70.0,
        },
    )
    db_session.add(snapshot)
    db_session.add(matching_snapshot)
    db_session.commit()

    db_session.delete(offer)
    db_session.commit()

    assert db_session.query(Application).filter(Application.id == application.id).one_or_none() is None
    assert (
        db_session.query(ApplicationSnapshot)
        .filter(ApplicationSnapshot.application_id == application.id)
        .one_or_none()
        is None
    )
    assert (
        db_session.query(ApplicationMatchingSnapshot)
        .filter(ApplicationMatchingSnapshot.application_id == application.id)
        .one_or_none()
        is None
    )


def test_deleting_seeker_user_cascades_to_applications_and_snapshots(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session, email="application-model-recruiter-cascade-user@example.com", role=UserRole.RECRUITER
    )
    seeker = _create_user(
        db_session, email="application-model-seeker-cascade-user@example.com", role=UserRole.JOB_SEEKER
    )
    offer = _create_job_offer(db_session, recruiter_user_id=recruiter.id)
    application = _create_application(
        db_session,
        job_offer_id=offer.id,
        seeker_user_id=seeker.id,
    )
    snapshot = ApplicationSnapshot(
        application_id=application.id,
        full_name="Alice Example",
        summary="Summary",
        location="Tallinn",
        occupation_key="backend_engineer",
        competencies=[{"competency_key": "comp_1", "level": "beginner"}],
        audit_metadata={"job_offer_title": "Backend Engineer"},
    )
    matching_snapshot = ApplicationMatchingSnapshot(
        application_id=application.id,
        algorithm_version="v2_exact_priority_level_dual_signal",
        score=72.5,
        result_payload={
            "algorithm_version": "v2_exact_priority_level_dual_signal",
            "scope": "shared_application_snapshot",
            "score": 72.5,
        },
    )
    db_session.add(snapshot)
    db_session.add(matching_snapshot)
    db_session.commit()

    db_session.delete(seeker)
    db_session.commit()

    assert db_session.query(Application).filter(Application.id == application.id).one_or_none() is None
    assert (
        db_session.query(ApplicationSnapshot)
        .filter(ApplicationSnapshot.application_id == application.id)
        .one_or_none()
        is None
    )
    assert (
        db_session.query(ApplicationMatchingSnapshot)
        .filter(ApplicationMatchingSnapshot.application_id == application.id)
        .one_or_none()
        is None
    )


def test_deleting_application_cascades_to_matching_snapshot(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session, email="application-model-delete-application-recruiter@example.com", role=UserRole.RECRUITER
    )
    seeker = _create_user(
        db_session, email="application-model-delete-application-seeker@example.com", role=UserRole.JOB_SEEKER
    )
    offer = _create_job_offer(db_session, recruiter_user_id=recruiter.id)
    application = _create_application(
        db_session,
        job_offer_id=offer.id,
        seeker_user_id=seeker.id,
    )
    _create_application_matching_snapshot(
        db_session,
        application_id=application.id,
    )

    db_session.delete(application)
    db_session.commit()

    assert (
        db_session.query(ApplicationMatchingSnapshot)
        .filter(ApplicationMatchingSnapshot.application_id == application.id)
        .one_or_none()
        is None
    )


def test_application_and_snapshot_timestamps_and_required_consent(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session, email="application-model-recruiter-timestamps@example.com", role=UserRole.RECRUITER
    )
    seeker = _create_user(
        db_session, email="application-model-seeker-timestamps@example.com", role=UserRole.JOB_SEEKER
    )
    offer = _create_job_offer(db_session, recruiter_user_id=recruiter.id)

    missing_consent = Application(
        job_offer_id=offer.id,
        seeker_user_id=seeker.id,
        consent_given_at=None,
    )
    db_session.add(missing_consent)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    application = _create_application(
        db_session,
        job_offer_id=offer.id,
        seeker_user_id=seeker.id,
    )
    snapshot = ApplicationSnapshot(
        application_id=application.id,
        full_name="Alice Example",
        summary=None,
        location="Tallinn",
        occupation_key="backend_engineer",
        competencies=[{"competency_key": "comp_1", "level": "intermediate"}],
        audit_metadata=None,
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)

    assert application.created_at is not None
    assert snapshot.created_at is not None


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("algorithm_version", None),
        ("score", None),
        ("result_payload", None),
    ],
)
def test_application_matching_snapshot_required_fields_are_enforced(db_session, field_name, field_value):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session, email=f"application-model-required-fields-recruiter-{field_name}@example.com", role=UserRole.RECRUITER
    )
    seeker = _create_user(
        db_session, email=f"application-model-required-fields-seeker-{field_name}@example.com", role=UserRole.JOB_SEEKER
    )
    offer = _create_job_offer(db_session, recruiter_user_id=recruiter.id)
    application = _create_application(
        db_session,
        job_offer_id=offer.id,
        seeker_user_id=seeker.id,
    )
    payload = {
        "application_id": application.id,
        "algorithm_version": "v2_exact_priority_level_dual_signal",
        "score": 65.0,
        "result_payload": {
            "algorithm_version": "v2_exact_priority_level_dual_signal",
            "scope": "shared_application_snapshot",
            "score": 65.0,
        },
    }
    payload[field_name] = field_value

    db_session.add(ApplicationMatchingSnapshot(**payload))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_application_matching_snapshot_created_at_is_autopopulated(db_session):
    _enable_sqlite_foreign_keys(db_session)
    recruiter = _create_user(
        db_session, email="application-model-matching-created-at-recruiter@example.com", role=UserRole.RECRUITER
    )
    seeker = _create_user(
        db_session, email="application-model-matching-created-at-seeker@example.com", role=UserRole.JOB_SEEKER
    )
    offer = _create_job_offer(db_session, recruiter_user_id=recruiter.id)
    application = _create_application(
        db_session,
        job_offer_id=offer.id,
        seeker_user_id=seeker.id,
    )

    snapshot = _create_application_matching_snapshot(
        db_session,
        application_id=application.id,
    )

    assert snapshot.created_at is not None
