from __future__ import annotations

import enum

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    JOB_SEEKER = "job_seeker"
    RECRUITER = "recruiter"


class CompetencyLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class RequirementPriority(str, enum.Enum):
    MUST_HAVE = "must_have"
    IMPORTANT = "important"
    NICE_TO_HAVE = "nice_to_have"


class JobOfferStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


def enum_column(enum_type: type[enum.Enum], *, name: str) -> Enum:
    return Enum(
        enum_type,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
        name=name,
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        enum_column(UserRole, name="userrole"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    job_seeker_profile: Mapped[JobSeekerProfile | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    recruiter_profile: Mapped[RecruiterProfile | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    competencies: Mapped[list[JobSeekerCompetency]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    job_offers: Mapped[list[JobOffer]] = relationship(
        back_populates="recruiter_user",
        cascade="all, delete-orphan",
    )
    refresh_token_sessions: Mapped[list[RefreshTokenSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class JobSeekerProfile(TimestampMixin, Base):
    __tablename__ = "job_seeker_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    occupation_key: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="job_seeker_profile")


class JobSeekerCompetency(Base):
    __tablename__ = "job_seeker_competencies"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "competency_key",
            name="uq_job_seeker_competencies_user_id_competency_key",
        ),
        Index(
            "ix_job_seeker_competencies_user_id",
            "user_id",
        ),
        Index(
            "ix_job_seeker_competencies_competency_key",
            "competency_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    competency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[CompetencyLevel] = mapped_column(
        enum_column(CompetencyLevel, name="competencylevel"),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="competencies")


class RecruiterProfile(Base):
    __tablename__ = "recruiter_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped[User] = relationship(back_populates="recruiter_profile")


class JobOffer(TimestampMixin, Base):
    __tablename__ = "job_offers"
    __table_args__ = (Index("ix_job_offers_recruiter_user_id", "recruiter_user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recruiter_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    occupation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[JobOfferStatus] = mapped_column(
        enum_column(JobOfferStatus, name="jobofferstatus"),
        nullable=False,
        default=JobOfferStatus.DRAFT,
        server_default=JobOfferStatus.DRAFT.value,
    )

    recruiter_user: Mapped[User] = relationship(back_populates="job_offers")
    requirements: Mapped[list[JobOfferRequirement]] = relationship(
        back_populates="job_offer",
        cascade="all, delete-orphan",
    )


class JobOfferRequirement(Base):
    __tablename__ = "job_offer_requirements"
    __table_args__ = (
        UniqueConstraint(
            "job_offer_id",
            "competency_key",
            name="uq_job_offer_requirements_job_offer_id_competency_key",
        ),
        Index("ix_job_offer_requirements_job_offer_id", "job_offer_id"),
        Index(
            "ix_job_offer_requirements_competency_key",
            "competency_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_offer_id: Mapped[int] = mapped_column(
        ForeignKey("job_offers.id", ondelete="CASCADE"),
        nullable=False,
    )
    competency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[RequirementPriority] = mapped_column(
        enum_column(RequirementPriority, name="requirementpriority"),
        nullable=False,
    )

    job_offer: Mapped[JobOffer] = relationship(back_populates="requirements")


class RefreshTokenSession(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="refresh_token_sessions")
