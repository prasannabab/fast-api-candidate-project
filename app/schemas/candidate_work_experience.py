"""candidate_work_experience.py (schemas) - Create/Update/Read models for job history records."""

import uuid                                            # PK/FK type
from datetime import date                                # start_date / end_date type
from pydantic import BaseModel, Field, ConfigDict, model_validator  # Building blocks + validator


class CandidateWorkExperienceBase(BaseModel):
    """Fields shared across create/update/read variants."""

    company_name: str = Field(..., min_length=1, max_length=255, description="Employer name")        # Required
    job_title: str = Field(..., min_length=1, max_length=150, description="Role/title held")            # Required
    location: str | None = Field(default=None, max_length=255, description="Work location or 'Remote'")   # Optional
    start_date: date = Field(..., description="Date employment started")                                    # Required
    end_date: date | None = Field(default=None, description="Date employment ended (omit if current job)")    # Optional
    is_current: bool = Field(default=False, description="Whether this is the candidate's current job")         # Defaults False
    description: str | None = Field(default=None, max_length=2000, description="Responsibilities/achievements")  # Optional

    @model_validator(mode="after")
    def validate_dates(self):
        """Ensures end_date (if provided) isn't before start_date, and is_current implies no end_date."""
        if self.end_date and self.end_date < self.start_date:      # Basic date-order sanity check
            raise ValueError("end_date cannot be earlier than start_date")
        if self.is_current and self.end_date is not None:            # A "current" job shouldn't have an end date
            raise ValueError("is_current jobs should not have an end_date")
        return self  # Required return for "after" validators


class CandidateWorkExperienceCreate(CandidateWorkExperienceBase):
    """Body shape for creating a new work-experience record."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company_name": "Phenom People",
                "job_title": "Senior Backend Developer",
                "location": "Hyderabad, India",
                "start_date": "2019-01-15",
                "end_date": "2026-07-31",
                "is_current": False,
                "description": "Built and maintained im-proxy-service, im-config-service microservices.",
            }
        }
    )


class CandidateWorkExperienceUpdate(BaseModel):
    """Partial-update (PATCH) body - every field optional."""

    company_name: str | None = Field(default=None, min_length=1, max_length=255)  # Optional new employer
    job_title: str | None = Field(default=None, min_length=1, max_length=150)        # Optional new title
    location: str | None = Field(default=None, max_length=255)                          # Optional new location
    start_date: date | None = Field(default=None)                                          # Optional new start date
    end_date: date | None = Field(default=None)                                              # Optional new end date
    is_current: bool | None = Field(default=None)                                              # Optional new current flag
    description: str | None = Field(default=None, max_length=2000)                                # Optional new description

    model_config = ConfigDict(extra="forbid")  # Reject unknown fields


class CandidateWorkExperienceRead(CandidateWorkExperienceBase):
    """Response shape returned to API clients."""

    id: uuid.UUID = Field(..., description="Work experience record id")   # Row PK
    candidate_id: uuid.UUID = Field(..., description="Owning candidate id")  # FK back to candidate

    model_config = ConfigDict(from_attributes=True)  # Build directly from ORM object
