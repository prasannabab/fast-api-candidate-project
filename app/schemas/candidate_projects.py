"""candidate_projects.py (schemas) - Create/Update/Read models for showcase projects."""

import uuid                                       # PK/FK type
from datetime import date                           # start_date / end_date type
from pydantic import BaseModel, Field, ConfigDict, HttpUrl  # Building blocks; HttpUrl validates project_url


class CandidateProjectBase(BaseModel):
    """Fields shared across create/update/read variants."""

    title: str = Field(..., min_length=1, max_length=255, description="Project name")                     # Required
    description: str | None = Field(default=None, max_length=3000, description="What the project does")     # Optional
    tech_stack: list[str] | None = Field(default=None, description="Technologies used, e.g. ['FastAPI','Postgres']")  # Optional list
    project_url: HttpUrl | None = Field(default=None, description="Link to repo or live demo")                  # Optional validated URL
    start_date: date | None = Field(default=None, description="When work on the project began")                   # Optional
    end_date: date | None = Field(default=None, description="When the project was completed")                       # Optional


class CandidateProjectCreate(CandidateProjectBase):
    """Body shape for creating a new project record."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Resume Matcher RAG",
                "description": "Local-first RAG resume matcher using FastAPI, pgvector, and Ollama.",
                "tech_stack": ["FastAPI", "pgvector", "Ollama", "nomic-embed-text"],
                "project_url": "https://github.com/prasannabab/resume-matcher-rag",
                "start_date": "2026-05-01",
                "end_date": "2026-07-15",
            }
        }
    )


class CandidateProjectUpdate(BaseModel):
    """Partial-update (PATCH) body - every field optional."""

    title: str | None = Field(default=None, min_length=1, max_length=255)   # Optional new title
    description: str | None = Field(default=None, max_length=3000)             # Optional new description
    tech_stack: list[str] | None = Field(default=None)                            # Optional new tech stack list
    project_url: HttpUrl | None = Field(default=None)                                # Optional new URL
    start_date: date | None = Field(default=None)                                       # Optional new start date
    end_date: date | None = Field(default=None)                                           # Optional new end date

    model_config = ConfigDict(extra="forbid")  # Reject unknown fields


class CandidateProjectRead(CandidateProjectBase):
    """Response shape returned to API clients."""

    id: uuid.UUID = Field(..., description="Project record id")            # Row PK
    candidate_id: uuid.UUID = Field(..., description="Owning candidate id")   # FK back to candidate

    model_config = ConfigDict(from_attributes=True)  # Build directly from ORM object
