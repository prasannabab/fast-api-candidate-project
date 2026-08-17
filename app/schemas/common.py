"""
common.py
---------
Shared Pydantic models reused across multiple routers:
- Pagination envelope for list responses
- A reusable "Query Parameter Model" for filtering/searching
- A reusable "Header Parameter Model" and "Cookie Parameter Model"
These demonstrate the FastAPI "Query Parameter Models" / "Cookie Parameter Models" /
"Header Parameter Models" tutorial topics in one shared place (DRY).
"""

from typing import Generic, TypeVar, List                 # Generics let us build one PaginatedResponse for any model type
from pydantic import BaseModel, Field                       # Base class + Field for extra validation/metadata

T = TypeVar("T")  # Generic type variable representing "whatever item type is being paginated"


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic envelope wrapping any list endpoint's results with paging metadata."""

    total: int = Field(..., description="Total number of matching rows in the database")  # Total row count (ignores paging)
    skip: int = Field(..., description="Number of rows skipped (offset)")                    # Echo back the offset used
    limit: int = Field(..., description="Max number of rows returned in this page")           # Echo back the page size used
    items: List[T] = Field(..., description="The page of results")                              # The actual page of data


class CandidateQueryParams(BaseModel):
    """
    Query Parameter Model (see FastAPI 'Query Parameter Models' docs):
    groups all the optional filter/search/pagination query params for listing
    candidates into a single reusable, validated object instead of many loose args.
    """

    search: str | None = Field(
        default=None, min_length=1, max_length=100,
        description="Free-text search across first name, last name, and email",
    )  # Optional search string with length validation
    location: str | None = Field(default=None, max_length=255, description="Filter by current_location")  # Optional location filter
    skip: int = Field(default=0, ge=0, description="Number of rows to skip (pagination offset)")  # Must be >= 0
    limit: int = Field(default=20, ge=1, le=100, description="Max rows to return (1-100)")           # Bounded page size

    model_config = {"extra": "forbid"}  # Reject unknown query params instead of silently ignoring them


class CommonHeaders(BaseModel):
    """
    Header Parameter Model (see FastAPI 'Header Parameter Models' docs):
    groups commonly-used inbound headers into one validated object.
    """

    x_request_id: str | None = Field(default=None, description="Client-supplied request/trace id")  # Optional tracing id
    user_agent: str | None = Field(default=None, description="Caller's User-Agent string")             # Standard UA header

    model_config = {"extra": "ignore"}  # Ignore any other headers the client happens to send


class SessionCookies(BaseModel):
    """
    Cookie Parameter Model (see FastAPI 'Cookie Parameter Models' docs):
    groups cookies the API reads on incoming requests.
    """

    session_id: str | None = Field(default=None, description="Opaque session identifier cookie")  # Optional session cookie
    csrf_token: str | None = Field(default=None, description="Double-submit CSRF cookie value")      # CSRF cookie value

    model_config = {"extra": "ignore"}  # Ignore unrelated cookies the browser might send
