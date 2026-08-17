"""
candidate_info.py (router)
----------------------------
CRUD endpoints for the CandidateInfo entity, plus several endpoints that exist
specifically to demonstrate remaining FastAPI tutorial topics: numeric path
validation, file uploads, background tasks, streamed JSON Lines, and SSE.
"""

import asyncio                                                  # Used to simulate async work in the SSE demo
import json                                                       # Used to build JSON Lines output
import os                                                           # Used to build the resume upload file path
import uuid                                                          # Path/body id type

from fastapi import (
    APIRouter, Depends, HTTPException, Path, Query, status,          # Core routing + param declarations
    BackgroundTasks, UploadFile, File, Form, Request,                   # Background tasks, file/form uploads, raw Request
)
from fastapi.encoders import jsonable_encoder                          # "JSON Compatible Encoder" topic
from fastapi.responses import StreamingResponse                          # Used for JSON Lines + SSE streaming
from sqlalchemy import select, or_                                          # Query building helpers
from sqlalchemy.orm import Session, selectinload                              # DB session type + eager-loading helper

from app.database import get_db                                    # Per-request DB session dependency
from app.models import CandidateInfo                                  # ORM model
from app.dependencies import get_candidate_or_404, get_common_headers, get_session_cookies  # Shared dependencies
from app.exceptions import DuplicateEmailError                           # Custom exception for duplicate emails
from app.rate_limiter import limiter                                        # Shared rate limiter
from app.security import get_current_user                                    # Auth dependency
from app.config import settings                                                # For the upload directory path
from app.schemas.common import PaginatedResponse, CandidateQueryParams, CommonHeaders, SessionCookies  # Shared schemas
from app.schemas.candidate_info import CandidateInfoCreate, CandidateInfoUpdate, CandidateInfoRead  # Entity schemas
from app.schemas.candidate_preferences import CandidateFullProfile                                       # Nested response schema

router = APIRouter(prefix="/candidates", tags=["Candidate Info"])  # Base path + docs grouping for this router


def _send_welcome_notification(email: str) -> None:
    """
    Pretend "send an email" function run in the background after candidate creation.
    In a real app this would call an email provider; here it just demonstrates the
    'Background Tasks' pattern - the HTTP response returns before this runs.
    """
    print(f"[background] would send a welcome email to {email}")  # Stand-in for a real notification side-effect


@router.post(
    "",                                                          # POST /candidates
    response_model=CandidateInfoRead,                                # "Response Model - Return Type": shape of the response
    status_code=status.HTTP_201_CREATED,                                # "Response Status Code": 201 for successful creation
    summary="Create a new candidate",                                     # "Path Operation Configuration"
    tags=["Candidate Info"],                                                 # Explicit tag (also settable at router level)
)
@limiter.limit(settings.rate_limit_default)  # Apply the shared default rate limit to this endpoint
async def create_candidate(
    request: Request,                                    # Required so slowapi can inspect the caller's IP
    payload: CandidateInfoCreate,                            # "Request Body": validated creation payload
    background_tasks: BackgroundTasks,                          # "Background Tasks": schedule work after responding
    db: Session = Depends(get_db),                                 # Injected DB session
    current_user: str = Depends(get_current_user),                   # "Security": require a valid bearer token
):
    """Creates a new candidate record. Requires authentication."""
    existing = db.execute(select(CandidateInfo).where(CandidateInfo.email == payload.email)).scalar_one_or_none()  # Uniqueness check
    if existing is not None:                                                  # Email already registered
        raise DuplicateEmailError(payload.email)                                 # Handled globally -> clean 409 response

    candidate = CandidateInfo(**payload.model_dump())    # Convert the validated Pydantic model into ORM constructor kwargs
    db.add(candidate)                                        # Stage the new row for insertion
    db.commit()                                                # Persist to Postgres
    db.refresh(candidate)                                        # Reload server-generated fields (id, created_at, etc.)

    background_tasks.add_task(_send_welcome_notification, candidate.email)  # Fire-and-forget after the response is sent
    return candidate  # FastAPI serializes this ORM object using CandidateInfoRead (from_attributes=True)


@router.get(
    "",                                                       # GET /candidates
    response_model=PaginatedResponse[CandidateInfoRead],          # Generic paginated envelope around CandidateInfoRead
    summary="List candidates with search & pagination",
)
@limiter.limit(settings.rate_limit_default)  # Rate limit list endpoint too
async def list_candidates(
    request: Request,                                          # Required by slowapi
    params: CandidateQueryParams = Depends(),                       # "Query Parameter Models": bundled filter/paging params
    headers: CommonHeaders = Depends(get_common_headers),               # "Header Parameter Models"
    cookies: SessionCookies = Depends(get_session_cookies),                # "Cookie Parameter Models"
    db: Session = Depends(get_db),                                          # Injected DB session
):
    """Lists candidates, optionally filtered by free-text search and/or location."""
    query = select(CandidateInfo)                                    # Base SELECT statement
    if params.search:                                                    # Optional free-text search across a few fields
        like_pattern = f"%{params.search}%"                                 # Simple ILIKE-style pattern
        query = query.where(
            or_(
                CandidateInfo.first_name.ilike(like_pattern),                   # Case-insensitive match on first name
                CandidateInfo.last_name.ilike(like_pattern),                       # ...or last name
                CandidateInfo.email.ilike(like_pattern),                             # ...or email
            )
        )
    if params.location:                                                        # Optional location filter
        query = query.where(CandidateInfo.current_location.ilike(f"%{params.location}%"))  # Partial, case-insensitive match

    total = len(db.execute(query).scalars().all())                                # Count matching rows (simple approach)
    rows = db.execute(query.offset(params.skip).limit(params.limit)).scalars().all()  # Apply pagination

    return PaginatedResponse[CandidateInfoRead](                                    # Wrap results in the paging envelope
        total=total, skip=params.skip, limit=params.limit, items=rows
    )


@router.get(
    "/top/{limit}",                                          # GET /candidates/top/{limit}
    response_model=list[CandidateInfoRead],
    summary="Get the N most recently created candidates",
)
async def get_top_candidates(
    limit: int = Path(
        ...,                                                    # Required path parameter
        gt=0,                                                       # "Path Parameters and Numeric Validations": must be > 0
        le=100,                                                        # ...and <= 100
        description="How many of the most recently created candidates to return",
    ),
    db: Session = Depends(get_db),  # Injected DB session
):
    """Demonstrates numeric path-parameter validation: returns the `limit` newest candidates."""
    rows = db.execute(
        select(CandidateInfo).order_by(CandidateInfo.created_at.desc()).limit(limit)  # Newest first, capped at `limit`
    ).scalars().all()
    return rows  # Serialized as a list of CandidateInfoRead


@router.get(
    "/stream",                                                # GET /candidates/stream
    summary="Stream all candidates as JSON Lines",
)
async def stream_candidates(db: Session = Depends(get_db)):
    """
    'Stream JSON Lines' topic: streams one JSON object per line instead of
    building one huge JSON array in memory - useful for very large result sets.
    """

    def line_generator():
        rows = db.execute(select(CandidateInfo)).scalars().all()      # Fetch all candidates (kept simple for the demo)
        for row in rows:                                                  # Emit one line per candidate
            payload = jsonable_encoder(CandidateInfoRead.model_validate(row))  # "JSON Compatible Encoder": ORM -> JSON-safe dict
            yield json.dumps(payload) + "\n"                                     # One compact JSON object per line

    return StreamingResponse(line_generator(), media_type="application/x-ndjson")  # ndjson = newline-delimited JSON


@router.get(
    "/{candidate_id}/events",                                   # GET /candidates/{candidate_id}/events
    summary="Server-Sent Events demo: streamed profile-processing progress",
)
async def candidate_processing_events(candidate: CandidateInfo = Depends(get_candidate_or_404)):
    """
    'Server-Sent Events (SSE)' topic: simulates a long-running profile-processing
    job (e.g. resume parsing) and streams progress updates to the client as they happen.
    """

    async def event_generator():
        steps = ["validating profile", "parsing resume", "extracting skills", "indexing for search", "done"]  # Demo steps
        for i, step in enumerate(steps, start=1):                     # Emit one SSE "event" per step
            await asyncio.sleep(0.5)                                     # Simulate work being done
            payload = {"step": i, "total": len(steps), "message": step}    # Progress payload
            yield f"data: {json.dumps(payload)}\n\n"                          # SSE wire format: "data: <json>\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")  # Correct MIME type for SSE


@router.get(
    "/{candidate_id}/full-profile",                             # GET /candidates/{candidate_id}/full-profile
    response_model=CandidateFullProfile,                             # "Body - Nested Models": nested child collections
    summary="Get a candidate with all nested education/experience/projects/preferences",
)
async def get_candidate_full_profile(candidate_id: uuid.UUID, db: Session = Depends(get_db)):
    """Loads a candidate together with every related child record in one query."""
    candidate = db.execute(
        select(CandidateInfo)
        .where(CandidateInfo.id == candidate_id)
        .options(                                                       # Eager-load all relationships to avoid N+1 queries
            selectinload(CandidateInfo.education),
            selectinload(CandidateInfo.work_experience),
            selectinload(CandidateInfo.projects),
            selectinload(CandidateInfo.preferences),
        )
    ).scalar_one_or_none()
    if candidate is None:                                                  # No matching candidate
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate  # Serialized into the nested CandidateFullProfile schema


@router.get(
    "/{candidate_id}",                                          # GET /candidates/{candidate_id}
    response_model=CandidateInfoRead,                                # "Response Model - Return Type"
    summary="Get a single candidate by id",
)
async def get_candidate(
    candidate_id: uuid.UUID = Path(..., description="The candidate's unique id"),  # "Path Parameters"
    candidate: CandidateInfo = Depends(get_candidate_or_404),                          # Reused lookup-or-404 dependency
):
    """Fetches a single candidate by id."""
    return candidate  # Already validated to exist by the dependency


@router.put(
    "/{candidate_id}",                                          # PUT /candidates/{candidate_id}
    response_model=CandidateInfoRead,
    summary="Fully replace a candidate record",
)
async def replace_candidate(
    payload: CandidateInfoCreate,                                   # Full replacement body (all required fields)
    candidate: CandidateInfo = Depends(get_candidate_or_404),           # Looked-up candidate (404 if missing)
    db: Session = Depends(get_db),                                        # Injected session
    current_user: str = Depends(get_current_user),                          # Requires auth
):
    """Replaces every field on an existing candidate with the values in `payload` (PUT semantics)."""
    for field, value in payload.model_dump().items():   # Overwrite every field with the new value
        setattr(candidate, field, value)                    # Apply each field to the ORM instance
    db.commit()                                                # Persist changes
    db.refresh(candidate)                                        # Reload any server-computed fields
    return candidate


@router.patch(
    "/{candidate_id}",                                          # PATCH /candidates/{candidate_id}
    response_model=CandidateInfoRead,
    summary="Partially update a candidate record",
)
async def update_candidate(
    payload: CandidateInfoUpdate,                                   # "Body - Updates": only fields to change
    candidate: CandidateInfo = Depends(get_candidate_or_404),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Applies only the fields the client actually sent, leaving the rest untouched."""
    update_data = payload.model_dump(exclude_unset=True)   # exclude_unset=True -> only fields explicitly provided by the client
    stored_model_data = jsonable_encoder(candidate)              # "JSON Compatible Encoder": snapshot current DB state as plain dict
    for field in stored_model_data:                                  # Walk every column on the existing record
        if field in update_data:                                        # If the client sent a new value for this field...
            setattr(candidate, field, update_data[field])                  # ...apply it
    db.commit()                                                            # Persist the merged changes
    db.refresh(candidate)                                                    # Reload from DB
    return candidate


@router.delete(
    "/{candidate_id}",                                          # DELETE /candidates/{candidate_id}
    status_code=status.HTTP_204_NO_CONTENT,                          # 204 = success, no response body
    summary="Delete a candidate and all their child records",
)
async def delete_candidate(
    candidate: CandidateInfo = Depends(get_candidate_or_404),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Deletes a candidate; cascade rules on the ORM relationships remove child rows too."""
    db.delete(candidate)   # Mark for deletion
    db.commit()               # Commit -> cascades delete education/work/projects/preferences rows
    return None                 # 204 responses must not return a body


@router.post(
    "/{candidate_id}/resume",                                   # POST /candidates/{candidate_id}/resume
    response_model=CandidateInfoRead,
    summary="Upload a candidate's resume file",
)
async def upload_resume(
    candidate: CandidateInfo = Depends(get_candidate_or_404),        # Ensures the candidate exists first
    resume_file: UploadFile = File(..., description="The resume file (PDF/DOCX)"),  # "Request Files"
    note: str | None = Form(default=None, description="Optional note about this resume version"),  # "Request Forms and Files"
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Saves an uploaded resume file to disk and records its path on the candidate."""
    os.makedirs(settings.upload_dir, exist_ok=True)                        # Ensure the upload directory exists
    safe_filename = f"{candidate.id}_{resume_file.filename}"                   # Prefix with candidate id to avoid collisions
    destination_path = os.path.join(settings.upload_dir, safe_filename)          # Full path on disk

    contents = await resume_file.read()                                             # Read the uploaded bytes asynchronously
    with open(destination_path, "wb") as f:                                            # Open destination file in binary-write mode
        f.write(contents)                                                                 # Write the resume bytes to disk

    candidate.resume_file_path = destination_path      # Record where the file was saved
    if note:                                                # If the caller included a form note...
        print(f"[upload] note for {candidate.id}: {note}")     # ...log it (placeholder for storing in an audit table)
    db.commit()                                              # Persist the updated resume path
    db.refresh(candidate)                                       # Reload the candidate row
    return candidate
