"""
middleware.py
--------------
Two pieces of custom Starlette middleware, demonstrating the FastAPI
'Middleware' tutorial topic:

1. TimingMiddleware   - adds an X-Process-Time-Ms response header (observability).
2. CSRFMiddleware      - implements the "double-submit cookie" CSRF defense: a
                          random token is set as a cookie on safe (GET) requests,
                          and any unsafe request (POST/PUT/PATCH/DELETE) must echo
                          that same token back in an X-CSRF-Token header.
"""

import hashlib                                                # Used to sign the CSRF token
import hmac                                                    # Constant-time comparison + HMAC signing
import secrets                                                  # Cryptographically secure random token generation
import time                                                       # Used to measure request duration

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint  # Base class for custom middleware
from starlette.requests import Request                              # Incoming request object
from starlette.responses import Response, JSONResponse                # Outgoing response objects

from app.config import settings  # Holds the CSRF signing secret

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}   # Methods that don't need CSRF protection (they shouldn't mutate state)
CSRF_COOKIE_NAME = "csrf_token"               # Name of the cookie holding the CSRF token
CSRF_HEADER_NAME = "X-CSRF-Token"               # Header clients must echo the token back in


def _sign(value: str) -> str:
    """HMAC-signs a value with our secret so tokens can't be forged by a client."""
    signature = hmac.new(settings.csrf_secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()  # HMAC-SHA256
    return f"{value}.{signature}"  # Combine raw token + signature so we can verify it later


def _generate_token() -> str:
    """Creates a new signed CSRF token."""
    raw = secrets.token_urlsafe(32)  # 32 bytes of cryptographically secure randomness, URL-safe encoded
    return _sign(raw)                  # Sign it so we can detect tampering


def _is_valid(token: str) -> bool:
    """Verifies a signed CSRF token's signature matches what we'd compute ourselves."""
    if not token or "." not in token:   # Malformed tokens are automatically invalid
        return False
    raw, _, signature = token.rpartition(".")   # Split back into the raw random part and its signature
    expected = hmac.new(settings.csrf_secret_key.encode(), raw.encode(), hashlib.sha256).hexdigest()  # Recompute signature
    return hmac.compare_digest(signature, expected)  # Constant-time comparison (avoids timing attacks)


class TimingMiddleware(BaseHTTPMiddleware):
    """Adds an X-Process-Time-Ms header to every response, useful for basic performance monitoring."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()          # High-resolution start timestamp
        response = await call_next(request)          # Let the request continue through the rest of the app
        duration_ms = (time.perf_counter() - start_time) * 1000  # Compute elapsed time in milliseconds
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"  # Attach the timing header to the outgoing response
        return response  # Return the (now-annotated) response


class CSRFMiddleware(BaseHTTPMiddleware):
    """Implements double-submit-cookie CSRF protection for all state-changing requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in SAFE_METHODS:  # GET/HEAD/OPTIONS can't mutate state, so they're always allowed
            response = await call_next(request)                     # Process the request normally
            if CSRF_COOKIE_NAME not in request.cookies:                # If the client has no CSRF cookie yet...
                response.set_cookie(
                    key=CSRF_COOKIE_NAME,        # ...issue them a fresh one
                    value=_generate_token(),        # New signed random token
                    httponly=False,                   # Must be readable by JS so the frontend can echo it in a header
                    samesite="strict",                  # Cookie only sent on same-site requests (extra CSRF defense)
                    secure=True,                          # Only sent over HTTPS in production
                )
            return response  # Return the normal response for safe methods

        # For unsafe methods (POST/PUT/PATCH/DELETE) we require a valid, matching token.
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)         # Token the browser sent as a cookie
        header_token = request.headers.get(CSRF_HEADER_NAME)          # Token the frontend JS sent as a header
        if not cookie_token or not header_token or cookie_token != header_token or not _is_valid(cookie_token):
            # Reject if either is missing, they don't match, or the signature is invalid/tampered.
            return JSONResponse(
                status_code=403,                                       # Forbidden
                content={"detail": "CSRF token missing or invalid"},      # Clear error message for the client
            )
        return await call_next(request)  # Token checks passed - continue processing the request

