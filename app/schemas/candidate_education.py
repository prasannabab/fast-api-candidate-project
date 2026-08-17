"""candidate_education.py (schemas) - Create/Update/Read models for education records."""

import uuid                                          # Primary/foreign key type
from datetime import date                              # start_date / end_date type
from pydantic import BaseModel, Field, ConfigDict, model_validator  # Building blocks + cross-field validator


class CandidateEducationBase(BaseModel):
    """Fields shared across create/update/read variants."""

    institution_name: str = Field(..., min_length=1, max_length=255, description="School or university name")  # Required
    degree: str = Field(..., min_length=1, max_length=150, description="Degree obtained, e.g. B.Tech")            # Required
    field_of_study: str | None = Field(default=None, max_length=150, description="Major/specialization")           # Optional
    start_date: date | None = Field(default=None, description="When studies started")                                # Optional
    end_date: date | None = Field(default=None, description="When studies ended (omit if ongoing)")                    # Optional
    grade: str | None = Field(default=None, max_length=50, description="GPA / percentage / grade obtained")             # Optional
    description: str | None = Field(default=None, max_length=2000, description="Free-text notes, honors, etc.")           # Optional

    @model_validator(mode="after")
    def validate_dates(self):
        """Cross-field validation: end_date can't be before start_date. Raises a 422 if violated."""
        if self.start_date and self.end_date and self.end_date < self.start_date:  # Compare the two dates
            raise ValueError("end_date cannot be earlier than start_date")            # Pydantic turns this into a clean 422 error
        return self  # Must return self from an "after" validator


class CandidateEducationCreate(CandidateEducationBase):
    """Body shape for creating a new education record under a given candidate."""

    model_config = ConfigDict(
        json_schema_extra={  # Example shown in Swagger UI
            "example": {
                "institution_name": "Indian Institute of Technology",
                "degree": "B.Tech",
                "field_of_study": "Computer Science",
                "start_date": "2014-07-01",
                "end_date": "2018-06-01",
                "grade": "8.7 CGPA",
                "description": "Graduated with honors; focused on distributed systems.",
            }
        }
    )


class CandidateEducationUpdate(BaseModel):
    """Partial-update (PATCH) body - every field optional."""

    institution_name: str | None = Field(default=None, min_length=1, max_length=255)   # Optional new institution
    degree: str | None = Field(default=None, min_length=1, max_length=150)                # Optional new degree
    field_of_study: str | None = Field(default=None, max_length=150)                        # Optional new major
    start_date: date | None = Field(default=None)                                             # Optional new start date
    end_date: date | None = Field(default=None)                                                 # Optional new end date
    grade: str | None = Field(default=None, max_length=50)                                        # Optional new grade
    description: str | None = Field(default=None, max_length=2000)                                   # Optional new description

    model_config = ConfigDict(extra="forbid")  # Reject unrecognized fields


class CandidateEducationRead(CandidateEducationBase):
    """Response shape returned to API clients."""

    id: uuid.UUID = Field(..., description="Education record id")             # Row primary key
    candidate_id: uuid.UUID = Field(..., description="Owning candidate id")      # FK back to candidate

    model_config = ConfigDict(from_attributes=True)  # Build directly from the SQLAlchemy ORM object
