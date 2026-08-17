"""candidate_preferences.py (schemas) - Create/Update/Read models for job-search preferences,
plus CandidateFullProfile which demonstrates 'Body - Nested Models' by embedding all
four child entities inside the parent CandidateInfo response."""

import uuid                                             # PK/FK type
from decimal import Decimal                                # "Extra Data Types": precise currency values
from enum import Enum                                        # Backing enum for preferred_job_type
from pydantic import BaseModel, Field, ConfigDict              # Building blocks

from app.schemas.candidate_info import CandidateInfoRead         # Reused for the nested full-profile schema
from app.schemas.candidate_education import CandidateEducationRead
from app.schemas.candidate_work_experience import CandidateWorkExperienceRead
from app.schemas.candidate_projects import CandidateProjectRead


class JobTypeSchema(str, Enum):
    """Pydantic mirror of the SQLAlchemy JobType enum, used for request/response validation."""
    FULL_TIME = "full_time"     # Full-time role preference
    PART_TIME = "part_time"     # Part-time role preference
    CONTRACT = "contract"          # Contract/freelance preference
    INTERNSHIP = "internship"       # Internship preference


class CandidatePreferencesBase(BaseModel):
    """Fields shared across create/update/read variants."""

    preferred_job_type: JobTypeSchema = Field(..., description="Type of role the candidate is looking for")  # Required enum
    preferred_locations: list[str] | None = Field(default=None, description="Cities/regions candidate prefers")  # Optional list
    expected_salary: Decimal | None = Field(default=None, ge=0, description="Expected annual salary (INR)")        # Optional, non-negative
    willing_to_relocate: bool = Field(default=False, description="Whether candidate is open to relocating")           # Defaults False
    notice_period_days: int | None = Field(default=None, ge=0, le=365, description="Notice period, in days")            # Bounded int


class CandidatePreferencesCreate(CandidatePreferencesBase):
    """Body shape for creating/setting a candidate's preferences."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "preferred_job_type": "full_time",
                "preferred_locations": ["Mumbai", "Bangalore", "Remote"],
                "expected_salary": 2500000,
                "willing_to_relocate": True,
                "notice_period_days": 30,
            }
        }
    )


class CandidatePreferencesUpdate(BaseModel):
    """Partial-update (PATCH) body - every field optional."""

    preferred_job_type: JobTypeSchema | None = Field(default=None)              # Optional new job type
    preferred_locations: list[str] | None = Field(default=None)                    # Optional new location list
    expected_salary: Decimal | None = Field(default=None, ge=0)                      # Optional new expected salary
    willing_to_relocate: bool | None = Field(default=None)                              # Optional new relocation flag
    notice_period_days: int | None = Field(default=None, ge=0, le=365)                    # Optional new notice period

    model_config = ConfigDict(extra="forbid")  # Reject unknown fields


class CandidatePreferencesRead(CandidatePreferencesBase):
    """Response shape returned to API clients."""

    id: uuid.UUID = Field(..., description="Preferences record id")          # Row PK
    candidate_id: uuid.UUID = Field(..., description="Owning candidate id")     # FK back to candidate (unique - 1:1)

    model_config = ConfigDict(from_attributes=True)  # Build directly from ORM object


class CandidateFullProfile(CandidateInfoRead):
    """
    'Body - Nested Models' example: the full candidate profile, embedding every
    child entity as a nested list/object inside the parent CandidateInfo response.
    Returned by GET /candidates/{candidate_id}/full-profile.
    """

    education: list[CandidateEducationRead] = Field(default_factory=list, description="All education records")  # Nested list
    work_experience: list[CandidateWorkExperienceRead] = Field(default_factory=list, description="All work history")  # Nested list
    projects: list[CandidateProjectRead] = Field(default_factory=list, description="All showcase projects")           # Nested list
    preferences: CandidatePreferencesRead | None = Field(default=None, description="Job-search preferences, if set")    # Nested object

    model_config = ConfigDict(from_attributes=True)  # Build directly from the ORM object graph (candidate + relationships)
