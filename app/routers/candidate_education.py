"""candidate_education.py (router) - CRUD for education records nested under a candidate."""

import uuid                                                     # Path parameter id type
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status, Request  # Routing building blocks
from sqlalchemy import select                                       # Query builder
from sqlalchemy.orm import Session                                    # DB session type

from app.database import get_db                                # Session dependency
from app.models import CandidateEducation, CandidateInfo             # ORM models
from app.dependencies import get_candidate_or_404                       # Shared parent-lookup dependency
from app.rate_limiter import limiter                                       # Shared rate limiter
from app.security import get_current_user                                     # Auth dependency
from app.config import settings                                                # Default rate-limit string
from app.schemas.candidate_education import (                                     # Entity schemas
    CandidateEducationCreate, CandidateEducationUpdate, CandidateEducationRead,
)

# Nested under /candidates/{candidate_id}/education - keeps the URL hierarchy self-documenting.
router = APIRouter(prefix="/candidates/{candidate_id}/education", tags=["Candidate Education"])


def _get_education_or_404(candidate_id: uuid.UUID, education_id: uuid.UUID, db: Session) -> CandidateEducation:
    """Looks up one education row scoped to its candidate, raising 404 if not found or mismatched."""
    row = db.execute(
        select(CandidateEducation).where(
            CandidateEducation.id == education_id,                     # Match the specific record
            CandidateEducation.candidate_id == candidate_id,               # ...and make sure it belongs to this candidate
        )
    ).scalar_one_or_none()
    if row is None:                                                          # Not found (or belongs to a different candidate)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education record not found")
    return row


@router.post(
    "",                                                              # POST /candidates/{candidate_id}/education
    response_model=CandidateEducationRead,
    status_code=status.HTTP_201_CREATED,                                 # Created
    summary="Add an education record to a candidate",
)
@limiter.limit(settings.rate_limit_default)  # Apply shared default rate limit
async def create_education(
    request: Request,                                             # Required by slowapi
    payload: CandidateEducationCreate,                                # Validated request body
    candidate: CandidateInfo = Depends(get_candidate_or_404),            # Ensures the parent candidate exists
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),                          # Requires auth
):
    """Creates a new education row linked to the given candidate."""
    row = CandidateEducation(**payload.model_dump(), candidate_id=candidate.id)  # Build ORM object, attach parent FK
    db.add(row)          # Stage for insert
    db.commit()             # Persist
    db.refresh(row)            # Reload generated fields (id)
    return row


@router.get(
    "",                                                              # GET /candidates/{candidate_id}/education
    response_model=list[CandidateEducationRead],
    summary="List a candidate's education records",
)
async def list_education(
    candidate: CandidateInfo = Depends(get_candidate_or_404),            # Ensures parent exists
    skip: int = Query(default=0, ge=0, description="Rows to skip"),          # "Query Parameters and String Validations" (numeric variant)
    limit: int = Query(default=20, ge=1, le=100, description="Max rows to return"),
    db: Session = Depends(get_db),
):
    """Lists education records for a candidate, paginated."""
    rows = db.execute(
        select(CandidateEducation)
        .where(CandidateEducation.candidate_id == candidate.id)     # Scope to this candidate only
        .offset(skip).limit(limit)                                      # Apply pagination
    ).scalars().all()
    return rows


@router.get(
    "/{education_id}",                                              # GET /candidates/{candidate_id}/education/{education_id}
    response_model=CandidateEducationRead,
    summary="Get a single education record",
)
async def get_education(
    candidate_id: uuid.UUID,                                              # Path param (also used inside the nested router prefix)
    education_id: uuid.UUID = Path(..., description="The education record's id"),  # "Path Parameters"
    db: Session = Depends(get_db),
):
    """Fetches one education record, scoped to its candidate."""
    return _get_education_or_404(candidate_id, education_id, db)  # Reuse the shared lookup helper


@router.put(
    "/{education_id}",
    response_model=CandidateEducationRead,
    summary="Fully replace an education record",
)
async def replace_education(
    candidate_id: uuid.UUID,
    education_id: uuid.UUID,
    payload: CandidateEducationCreate,                                      # Full replacement body
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Overwrites every field on an existing education record."""
    row = _get_education_or_404(candidate_id, education_id, db)   # Load or 404
    for field, value in payload.model_dump().items():                # Overwrite every field
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.patch(
    "/{education_id}",
    response_model=CandidateEducationRead,
    summary="Partially update an education record",
)
async def update_education(
    candidate_id: uuid.UUID,
    education_id: uuid.UUID,
    payload: CandidateEducationUpdate,                                       # Only fields to change
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Applies only the client-supplied fields, leaving the rest unchanged."""
    row = _get_education_or_404(candidate_id, education_id, db)
    update_data = payload.model_dump(exclude_unset=True)   # Only explicitly-sent fields
    for field, value in update_data.items():                    # Apply each provided field
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete(
    "/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an education record",
)
async def delete_education(
    candidate_id: uuid.UUID,
    education_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Deletes a single education record."""
    row = _get_education_or_404(candidate_id, education_id, db)   # Load or 404
    db.delete(row)     # Mark for deletion
    db.commit()           # Persist
    return None              # No content
