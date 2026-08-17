"""
dependencies.py
-----------------
Reusable `Depends()` callables shared across routers - the FastAPI 'Dependencies'
tutorial topic. Keeping them here (rather than duplicated per-router) supports
SOLID's Dependency Inversion Principle: routers depend on these abstractions,
not on concrete DB/session-lookup logic.
"""

import uuid                                                    # Used to validate/parse candidate_id path params
from fastapi import Depends, HTTPException, Header, Cookie, status  # DI + param declarations + error helper
from sqlalchemy.orm import Session                                # Type hint for the injected DB session

from app.database import get_db                    # Base session-per-request dependency
from app.models import CandidateInfo                  # Needed to look up "does this candidate exist"
from app.schemas.common import CommonHeaders, SessionCookies  # Header/Cookie parameter models


def get_common_headers(
    x_request_id: str | None = Header(default=None, description="Optional client trace id"),  # "Header Parameters"
    user_agent: str | None = Header(default=None),                                                # Standard header
) -> CommonHeaders:
    """Bundles individual header params into a validated CommonHeaders object for handlers to use."""
    return CommonHeaders(x_request_id=x_request_id, user_agent=user_agent)  # Wrap raw header values in our schema


def get_session_cookies(
    session_id: str | None = Cookie(default=None, description="Opaque session id"),   # "Cookie Parameters"
    csrf_token: str | None = Cookie(default=None),                                          # CSRF cookie (also read by middleware)
) -> SessionCookies:
    """Bundles individual cookie params into a validated SessionCookies object for handlers to use."""
    return SessionCookies(session_id=session_id, csrf_token=csrf_token)  # Wrap raw cookie values in our schema


def get_candidate_or_404(candidate_id: uuid.UUID, db: Session = Depends(get_db)) -> CandidateInfo:
    """
    Shared "look up parent candidate or raise 404" dependency, reused by every
    child-entity router (education/work-experience/projects/preferences) so they
    don't each reimplement the same existence check (SOLID - avoid duplication).
    """
    candidate = db.get(CandidateInfo, candidate_id)   # Primary-key lookup (fast, uses the index)
    if candidate is None:                                 # No row with that id
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,           # "Not Found"
            detail=f"Candidate with id {candidate_id} was not found",  # Human-readable error message
        )
    return candidate  # Hand the loaded ORM object to the calling path operation
