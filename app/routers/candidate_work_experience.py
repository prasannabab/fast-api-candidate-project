"""candidate_work_experience.py (router) - CRUD for work-experience records nested under a candidate."""

import uuid                                                      # Path parameter id type
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status, Request  # Routing building blocks
from sqlalchemy import select                                        # Query builder
from sqlalchemy.orm import Session                                     # DB session type

from app.database import get_db                                 # Session dependency
from app.models import CandidateWorkExperience, CandidateInfo         # ORM models
from app.dependencies import get_candidate_or_404                        # Shared parent-lookup dependency
from app.rate_limiter import limiter                                        # Shared rate limiter
from app.security import get_current_user                                      # Auth dependency
from app.config import settings                                                 # Default rate-limit string
from app.schemas.candidate_work_experience import (                                # Entity schemas
    CandidateWorkExperienceCreate, CandidateWorkExperienceUpdate, CandidateWorkExperienceRead,
)

router = APIRouter(prefix="/candidates/{candidate_id}/work-experience", tags=["Candidate Work Experience"])  # Nested route group


def _get_experience_or_404(candidate_id: uuid.UUID, experience_id: uuid.UUID, db: Session) -> CandidateWorkExperience:
    """Looks up a work-experience row scoped to its candidate, raising 404 if missing."""
    row = db.execute(
        select(CandidateWorkExperience).where(
            CandidateWorkExperience.id == experience_id,               # Match the specific record
            CandidateWorkExperience.candidate_id == candidate_id,          # ...owned by this candidate
        )
    ).scalar_one_or_none()
    if row is None:                                                        # Not found / mismatched candidate
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work experience record not found")
    return row


@router.post(
    "",
    response_model=CandidateWorkExperienceRead,
    status_code=status.HTTP_201_CREATED,                                     # Created
    summary="Add a work-experience record to a candidate",
)
@limiter.limit(settings.rate_limit_default)  # Shared default rate limit
async def create_work_experience(
    request: Request,                                              # Required by slowapi
    payload: CandidateWorkExperienceCreate,                            # Validated request body
    candidate: CandidateInfo = Depends(get_candidate_or_404),             # Ensures parent candidate exists
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),                            # Requires auth
):
    """Creates a new work-experience row linked to the given candidate."""
    row = CandidateWorkExperience(**payload.model_dump(), candidate_id=candidate.id)  # Build ORM object with parent FK
    db.add(row)       # Stage
    db.commit()          # Persist
    db.refresh(row)         # Reload generated id
    return row


@router.get(
    "",
    response_model=list[CandidateWorkExperienceRead],
    summary="List a candidate's work-experience records",
)
async def list_work_experience(
    candidate: CandidateInfo = Depends(get_candidate_or_404),
    skip: int = Query(default=0, ge=0),               # Pagination offset
    limit: int = Query(default=20, ge=1, le=100),          # Pagination size, bounded
    db: Session = Depends(get_db),
):
    """Lists work-experience records for a candidate, paginated."""
    rows = db.execute(
        select(CandidateWorkExperience)
        .where(CandidateWorkExperience.candidate_id == candidate.id)   # Scope to candidate
        .order_by(CandidateWorkExperience.start_date.desc())               # Most recent job first
        .offset(skip).limit(limit)                                            # Pagination
    ).scalars().all()
    return rows


@router.get(
    "/{experience_id}",
    response_model=CandidateWorkExperienceRead,
    summary="Get a single work-experience record",
)
async def get_work_experience(
    candidate_id: uuid.UUID,
    experience_id: uuid.UUID = Path(..., description="The work-experience record's id"),  # "Path Parameters"
    db: Session = Depends(get_db),
):
    """Fetches one work-experience record."""
    return _get_experience_or_404(candidate_id, experience_id, db)


@router.put(
    "/{experience_id}",
    response_model=CandidateWorkExperienceRead,
    summary="Fully replace a work-experience record",
)
async def replace_work_experience(
    candidate_id: uuid.UUID,
    experience_id: uuid.UUID,
    payload: CandidateWorkExperienceCreate,                       # Full replacement body
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Overwrites every field on an existing work-experience record."""
    row = _get_experience_or_404(candidate_id, experience_id, db)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.patch(
    "/{experience_id}",
    response_model=CandidateWorkExperienceRead,
    summary="Partially update a work-experience record",
)
async def update_work_experience(
    candidate_id: uuid.UUID,
    experience_id: uuid.UUID,
    payload: CandidateWorkExperienceUpdate,                        # Only fields to change
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Applies only client-supplied fields."""
    row = _get_experience_or_404(candidate_id, experience_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete(
    "/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a work-experience record",
)
async def delete_work_experience(
    candidate_id: uuid.UUID,
    experience_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Deletes a single work-experience record."""
    row = _get_experience_or_404(candidate_id, experience_id, db)
    db.delete(row)
    db.commit()
    return None
