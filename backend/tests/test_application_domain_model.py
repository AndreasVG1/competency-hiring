from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.models import (
    Application,
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
    db_session.add(snapshot)
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
    db_session.add(snapshot)
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
        consent_given_at=None,  # type: ignore[arg-type]
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
