"""
candidate_info.py (schemas)
----------------------------
Demonstrates 'Extra Models' (Create/Update/Read variants), 'Body - Fields',
'Extra Data Types' (EmailStr, HttpUrl, date, UUID), 'Declare Request Example Data',
and 'Body - Nested Models' (CandidateFullProfile nests the other four entities).
"""

import uuid                                                 # UUID type used for primary keys
from datetime import date, datetime                          # date/datetime "extra data types"
from pydantic import BaseModel, EmailStr, HttpUrl, Field, ConfigDict  # Pydantic building blocks


class CandidateInfoBase(BaseModel):
    """Fields shared by every variant (create/update/read) - avoids repeating ourselves."""

    first_name: str = Field(..., min_length=1, max_length=100, description="Candidate's first name")  # Required, bounded length
    last_name: str = Field(..., min_length=1, max_length=100, description="Candidate's last name")     # Required, bounded length
    email: EmailStr = Field(..., description="Unique contact email")                                     # Validated email format ("Extra Data Types")
    phone: str | None = Field(default=None, max_length=20, description="Contact phone number")            # Optional phone
    date_of_birth: date | None = Field(default=None, description="Date of birth (YYYY-MM-DD)")              # Optional date
    current_location: str | None = Field(default=None, max_length=255, description="City/country candidate lives in")
    linkedin_url: HttpUrl | None = Field(default=None, description="LinkedIn profile URL")                    # Validated URL type


class CandidateInfoCreate(CandidateInfoBase):
    """Shape required to CREATE a new candidate (POST request body)."""

    model_config = ConfigDict(
        json_schema_extra={  # "Declare Request Example Data": shown in the interactive docs
            "example": {
                "first_name": "Prasanna",
                "last_name": "Babu",
                "email": "prasanna.babu@example.com",
                "phone": "+91-9876543210",
                "date_of_birth": "1996-04-12",
                "current_location": "Mumbai, India",
                "linkedin_url": "https://www.linkedin.com/in/prasanna-babu",
            }
        }
    )


class CandidateInfoUpdate(BaseModel):
    """
    Shape used for PARTIAL updates (PATCH). Every field is Optional so the client
    only has to send the fields it wants to change - see 'Body - Updates' tutorial.
    """

    first_name: str | None = Field(default=None, min_length=1, max_length=100)   # Optional overwrite of first name
    last_name: str | None = Field(default=None, min_length=1, max_length=100)      # Optional overwrite of last name
    email: EmailStr | None = Field(default=None)                                     # Optional overwrite of email
    phone: str | None = Field(default=None, max_length=20)                            # Optional overwrite of phone
    date_of_birth: date | None = Field(default=None)                                   # Optional overwrite of DOB
    current_location: str | None = Field(default=None, max_length=255)                  # Optional overwrite of location
    linkedin_url: HttpUrl | None = Field(default=None)                                    # Optional overwrite of LinkedIn URL

    model_config = ConfigDict(extra="forbid")  # Reject unknown fields in the PATCH body


class CandidateInfoRead(CandidateInfoBase):
    """Shape returned to clients (response_model) - includes server-generated fields."""

    id: uuid.UUID = Field(..., description="Server-generated candidate id")   # Primary key
    resume_file_path: str | None = Field(default=None, description="Path of the uploaded resume, if any")  # Resume path
    created_at: datetime = Field(..., description="When this record was created")  # Audit timestamp
    updated_at: datetime = Field(..., description="When this record was last updated")  # Audit timestamp

    model_config = ConfigDict(from_attributes=True)  # Allows building this schema directly from an ORM object


class CandidateInfoInDB(CandidateInfoRead):
    """
    Internal-only representation (superset of CandidateInfoRead).
    Demonstrates the 'Extra Models' pattern of Base/Create/Update/Read/InDB variants -
    useful if later we add sensitive fields (e.g. hashed_password) that should
    exist in the DB model but never be serialized back in CandidateInfoRead.
    """
    pass  # Currently identical to Read; kept separate so DB-only fields can be added later without touching the public schema
