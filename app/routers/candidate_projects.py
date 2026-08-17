"""candidate_projects.py (router) - CRUD for project records nested under a candidate."""

import uuid                                                      # Path parameter id type
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status, Request  # Routing building blocks
from sqlalchemy import select                                        # Query builder
from sqlalchemy.orm import Session                                     # DB session type

from app.database import get_db                                 # Session dependency
from app.models import CandidateProject, CandidateInfo                # ORM models
from app.dependencies import get_candidate_or_404                        # Shared parent-lookup dependency
from app.rate_limiter import limiter                                        # Shared rate limiter
from app.security import get_current_user                                      # Auth dependency
from app.config import settings                                                 # Default rate-limit string
from app.schemas.candidate_projects import (                                       # Entity schemas
    CandidateProjectCreate, CandidateProjectUpdate, CandidateProjectRead,
)

router = APIRouter(prefix="/candidates/{candidate_id}/projects", tags=["Candidate Projects"])  # Nested route group


def _get_project_or_404(candidate_id: uuid.UUID, project_id: uuid.UUID, db: Session) -> CandidateProject:
    """Looks up a project row scoped to its candidate, raising 404 if missing."""
    row = db.execute(
        select(CandidateProject).where(
            CandidateProject.id == project_id,                     # Match the specific record
            CandidateProject.candidate_id == candidate_id,             # ...owned by this candidate
        )
    ).scalar_one_or_none()
    if row is None:                                                     # Not found / mismatched candidate
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project record not found")
    return row


@router.post(
    "",
    response_model=CandidateProjectRead,
    status_code=status.HTTP_201_CREATED,                                    # Created
    summary="Add a project record to a candidate",
)
@limiter.limit(settings.rate_limit_default)  # Shared default rate limit
async def create_project(
    request: Request,                                                # Required by slowapi
    payload: CandidateProjectCreate,                                     # Validated request body
    candidate: CandidateInfo = Depends(get_candidate_or_404),               # Ensures parent candidate exists
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),                             # Requires auth
):
    """Creates a new project row linked to the given candidate."""
    data = payload.model_dump()                              # Convert to plain dict
    data["project_url"] = str(data["project_url"]) if data.get("project_url") else None  # HttpUrl -> plain str for the DB column
    row = CandidateProject(**data, candidate_id=candidate.id)     # Build ORM object with parent FK
    db.add(row)      # Stage
    db.commit()         # Persist
    db.refresh(row)        # Reload generated id
    return row


@router.get(
    "",
    response_model=list[CandidateProjectRead],
    summary="List a candidate's projects",
)
async def list_projects(
    candidate: CandidateInfo = Depends(get_candidate_or_404),
    skip: int = Query(default=0, ge=0),               # Pagination offset
    limit: int = Query(default=20, ge=1, le=100),          # Pagination size
    db: Session = Depends(get_db),
):
    """Lists project records for a candidate, paginated."""
    rows = db.execute(
        select(CandidateProject)
        .where(CandidateProject.candidate_id == candidate.id)   # Scope to candidate
        .offset(skip).limit(limit)                                  # Pagination
    ).scalars().all()
    return rows


@router.get(
    "/{project_id}",
    response_model=CandidateProjectRead,
    summary="Get a single project record",
)
async def get_project(
    candidate_id: uuid.UUID,
    project_id: uuid.UUID = Path(..., description="The project record's id"),  # "Path Parameters"
    db: Session = Depends(get_db),
):
    """Fetches one project record."""
    return _get_project_or_404(candidate_id, project_id, db)


@router.put(
    "/{project_id}",
    response_model=CandidateProjectRead,
    summary="Fully replace a project record",
)
async def replace_project(
    candidate_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: CandidateProjectCreate,                       # Full replacement body
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Overwrites every field on an existing project record."""
    row = _get_project_or_404(candidate_id, project_id, db)
    data = payload.model_dump()
    data["project_url"] = str(data["project_url"]) if data.get("project_url") else None  # Normalize URL type again
    for field, value in data.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.patch(
    "/{project_id}",
    response_model=CandidateProjectRead,
    summary="Partially update a project record",
)
async def update_project(
    candidate_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: CandidateProjectUpdate,                        # Only fields to change
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Applies only client-supplied fields."""
    row = _get_project_or_404(candidate_id, project_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    if "project_url" in update_data and update_data["project_url"] is not None:  # Normalize URL type if present
        update_data["project_url"] = str(update_data["project_url"])
    for field, value in update_data.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project record",
)
async def delete_project(
    candidate_id: uuid.UUID,
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Deletes a single project record."""
    row = _get_project_or_404(candidate_id, project_id, db)
    db.delete(row)
    db.commit()
    return None
