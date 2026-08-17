"""
models.py
---------
SQLAlchemy ORM models = the actual Postgres table definitions.
One class per table. Relationships are declared so we can load a candidate
with all of their nested education/experience/projects/preferences in one go
(used later for the "Body - Nested Models" / "Extra Models" response schemas).
"""

import enum                                                # Used to define the JobType enum stored in Postgres
import uuid                                                 # Used to generate UUID primary keys
from datetime import datetime, date                          # Column types for timestamps and dates

from sqlalchemy import (
    String, Text, Date, DateTime, ForeignKey, Boolean,        # Column type classes
    Enum as SAEnum, Numeric, Integer, ARRAY, func,             # More column types + `func.now()` helper
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID     # Postgres-native UUID column type
from sqlalchemy.orm import Mapped, mapped_column, relationship  # SQLAlchemy 2.0 typed ORM helpers

from app.database import Base  # Our shared declarative base class


class JobType(str, enum.Enum):
    """Enum of allowed job-type preference values, stored as a Postgres ENUM type."""
    FULL_TIME = "full_time"    # Candidate wants a full-time role
    PART_TIME = "part_time"    # Candidate wants a part-time role
    CONTRACT = "contract"        # Candidate wants contract/freelance work
    INTERNSHIP = "internship"    # Candidate wants an internship


class CandidateInfo(Base):
    """Core candidate/person record - the "parent" entity all others hang off of."""

    __tablename__ = "candidate_info"  # Actual Postgres table name

    # Primary key: UUID instead of a plain int, generated in Python before insert.
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)          # Candidate's first name
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)            # Candidate's last name
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)  # Unique login/contact email
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)             # Optional phone number
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)           # Optional DOB
    current_location: Mapped[str | None] = mapped_column(String(255), nullable=True)   # City/country candidate lives in
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)        # Optional LinkedIn profile link
    resume_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)     # Path to uploaded resume file
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # Row creation time
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()   # Auto-updated on every UPDATE
    )

    # --- Relationships (one candidate -> many rows in each child table) ---
    education: Mapped[list["CandidateEducation"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"  # Deleting a candidate deletes their education rows too
    )
    work_experience: Mapped[list["CandidateWorkExperience"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    projects: Mapped[list["CandidateProject"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    preferences: Mapped["CandidatePreferences | None"] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", uselist=False  # One-to-one: only a single row
    )


class CandidateEducation(Base):
    """One row per school/degree a candidate has completed or is pursuing."""

    __tablename__ = "candidate_education"  # Postgres table name

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # Row PK
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("candidate_info.id", ondelete="CASCADE"), nullable=False, index=True
    )  # FK back to the owning candidate
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)   # School/university name
    degree: Mapped[str] = mapped_column(String(150), nullable=False)              # e.g. "Bachelor of Technology"
    field_of_study: Mapped[str | None] = mapped_column(String(150), nullable=True)  # e.g. "Computer Science"
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)            # When studies started
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)               # When studies ended (null = ongoing)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)              # GPA/percentage/grade
    description: Mapped[str | None] = mapped_column(Text, nullable=True)               # Free-text notes

    candidate: Mapped["CandidateInfo"] = relationship(back_populates="education")  # Back-reference to parent candidate


class CandidateWorkExperience(Base):
    """One row per job a candidate has held."""

    __tablename__ = "candidate_work_experience"  # Postgres table name

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("candidate_info.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)         # Employer name
    job_title: Mapped[str] = mapped_column(String(150), nullable=False)             # Role/title held
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)          # City/remote/etc
    start_date: Mapped[date] = mapped_column(Date, nullable=False)                    # Employment start date
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)                 # Employment end date (null = current job)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)     # Whether this is the current job
    description: Mapped[str | None] = mapped_column(Text, nullable=True)                   # Responsibilities/achievements

    candidate: Mapped["CandidateInfo"] = relationship(back_populates="work_experience")  # Back-reference to parent


class CandidateProject(Base):
    """One row per personal/professional project a candidate wants to showcase."""

    __tablename__ = "candidate_projects"  # Postgres table name

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("candidate_info.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)                 # Project name
    description: Mapped[str | None] = mapped_column(Text, nullable=True)              # What the project does
    tech_stack: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)  # e.g. ["FastAPI", "Postgres"]
    project_url: Mapped[str | None] = mapped_column(String(500), nullable=True)          # Link to repo/live demo
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)                   # When work began
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)                      # When work finished

    candidate: Mapped["CandidateInfo"] = relationship(back_populates="projects")  # Back-reference to parent


class CandidatePreferences(Base):
    """Single row per candidate describing their job-search preferences."""

    __tablename__ = "candidate_preferences"  # Postgres table name

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("candidate_info.id", ondelete="CASCADE"), nullable=False, unique=True
    )  # unique=True enforces the one-to-one relationship at the DB level
    preferred_job_type: Mapped[JobType] = mapped_column(SAEnum(JobType), nullable=False)  # full_time/part_time/etc
    preferred_locations: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)  # List of preferred cities
    expected_salary: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)  # Expected annual salary
    willing_to_relocate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Relocation flag
    notice_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Notice period in days

    candidate: Mapped["CandidateInfo"] = relationship(back_populates="preferences")  # Back-reference to parent
