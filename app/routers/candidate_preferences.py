"""candidate_preferences.py (router) - CRUD for the one-to-one preferences record under a candidate."""

import uuid                                                     # FK type
from fastapi import APIRouter, Depends, HTTPException, status, Request  # Routing building blocks
from sqlalchemy import select                                       # Query builder
from sqlalchemy.orm import Session                                    # DB session type

from app.database import get_db                                # Session dependency
from app.models import CandidatePreferences, CandidateInfo            # ORM models
from app.dependencies import get_candidate_or_404                       # Shared parent-lookup dependency
from app.rate_limiter import limiter                                       # Shared rate limiter
from app.security import get_current_user                                     # Auth dependency
from app.config import settings                                                # Default rate-limit string
from app.schemas.candidate_preferences import (                                   # Entity schemas
    CandidatePreferencesCreate, CandidatePreferencesUpdate, CandidatePreferencesRead,
)

# Note: no {preferences_id} in the URL - since this is one-to-one, the candidate_id alone identifies the row.
router = APIRouter(prefix="/candidates/{candidate_id}/preferences", tags=["Candidate Preferences"])


def _get_preferences_or_404(candidate_id: uuid.UUID, db: Session) -> CandidatePreferences:
    """Looks up the single preferences row for a candidate, raising 404 if not yet set."""
    row = db.execute(
        select(CandidatePreferences).where(CandidatePreferences.candidate_id == candidate_id)  # One row per candidate
    ).scalar_one_or_none()
    if row is None:                                                              # Preferences not set yet
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not set for this candidate")
    return row


@router.post(
    "",
    response_model=CandidatePreferencesRead,
    status_code=status.HTTP_201_CREATED,                                            # Created
    summary="Set a candidate's job-search preferences",
)
@limiter.limit(settings.rate_limit_default)  # Shared default rate limit
async def create_preferences(
    request: Request,                                                     # Required by slowapi
    payload: CandidatePreferencesCreate,                                       # Validated request body
    candidate: CandidateInfo = Depends(get_candidate_or_404),                      # Ensures parent candidate exists
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),                                    # Requires auth
):
    """Creates the preferences row for a candidate (fails if one already exists, via the DB unique constraint)."""
    existing = db.execute(
        select(CandidatePreferences).where(CandidatePreferences.candidate_id == candidate.id)  # Enforce 1:1 at the app level too
    ).scalar_one_or_none()
    if existing is not None:                                                             # Already has preferences
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,                                            # Conflict - use PATCH/PUT instead
            detail="Preferences already exist for this candidate; use PUT/PATCH to update them",
        )
    row = CandidatePreferences(**payload.model_dump(), candidate_id=candidate.id)  # Build ORM object with parent FK
    db.add(row)      # Stage
    db.commit()         # Persist
    db.refresh(row)        # Reload generated id
    return row


@router.get(
    "",
    response_model=CandidatePreferencesRead,
    summary="Get a candidate's job-search preferences",
)
async def get_preferences(
    candidate_id: uuid.UUID,
    candidate: CandidateInfo = Depends(get_candidate_or_404),  # Ensures the candidate itself exists
    db: Session = Depends(get_db),
):
    """Fetches the preferences row for a candidate."""
    return _get_preferences_or_404(candidate_id, db)


@router.put(
    "",
    response_model=CandidatePreferencesRead,
    summary="Fully replace a candidate's preferences",
)
async def replace_preferences(
    candidate_id: uuid.UUID,
    payload: CandidatePreferencesCreate,                    # Full replacement body
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Overwrites every field on the candidate's preferences record."""
    row = _get_preferences_or_404(candidate_id, db)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.patch(
    "",
    response_model=CandidatePreferencesRead,
    summary="Partially update a candidate's preferences",
)
async def update_preferences(
    candidate_id: uuid.UUID,
    payload: CandidatePreferencesUpdate,                     # Only fields to change
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Applies only client-supplied fields."""
    row = _get_preferences_or_404(candidate_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a candidate's preferences",
)
async def delete_preferences(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Deletes the candidate's preferences record."""
    row = _get_preferences_or_404(candidate_id, db)
    db.delete(row)
    db.commit()
    return None
