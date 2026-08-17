"""
main.py
--------
Application entry point. Demonstrates 'Metadata and Docs URLs', 'Middleware',
'CORS', and 'Bigger Applications - Multiple Files' (by including every router
built in app/routers/*). Run with:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI, Request, status                    # Core app class + request/status helpers
from fastapi.middleware.cors import CORSMiddleware                  # Built-in CORS middleware
from fastapi.responses import JSONResponse                            # Used in the rate-limit error handler
from slowapi.errors import RateLimitExceeded                            # Exception slowapi raises when a limit is hit
from slowapi.middleware import SlowAPIMiddleware                          # Middleware that enforces default_limits globally

from app.config import settings                       # Centralized settings (app name, version, CORS origins, etc.)
from app.database import Base, engine                     # Declarative base + engine, used to create tables on startup
from app.rate_limiter import limiter                          # Shared Limiter instance
from app.middleware import TimingMiddleware, CSRFMiddleware      # Our custom middleware
from app.exceptions import register_exception_handlers              # Registers custom exception -> response mappings

from app.routers import (                              # Import every router module ("Bigger Applications" pattern)
    auth, candidate_info, candidate_education,
    candidate_work_experience, candidate_projects, candidate_preferences,
)

# "Metadata and Docs URLs": customize the title/description/version shown in OpenAPI + control docs URLs.
app = FastAPI(
    title=settings.app_name,                                   # Shown at the top of /docs
    description="CRUD API for managing candidate profiles: info, education, work experience, projects, and preferences.",
    version=settings.app_version,                                 # Shown in /docs and the OpenAPI schema
    docs_url="/docs",                                               # Swagger UI location (default, made explicit)
    redoc_url="/redoc",                                               # ReDoc UI location (default, made explicit)
    openapi_tags=[                                                      # Custom ordering/descriptions for docs sections
        {"name": "Authentication", "description": "Obtain access tokens"},
        {"name": "Candidate Info", "description": "Core candidate profile CRUD"},
        {"name": "Candidate Education", "description": "Education history CRUD"},
        {"name": "Candidate Work Experience", "description": "Employment history CRUD"},
        {"name": "Candidate Projects", "description": "Showcase project CRUD"},
        {"name": "Candidate Preferences", "description": "Job-search preference CRUD"},
    ],
)

# --- Rate limiting wiring ---
app.state.limiter = limiter  # slowapi reads the limiter off app.state so decorated routes can find it


@app.exception_handler(RateLimitExceeded)  # "Handling Errors": custom handler for the rate-limit exception
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Turns a RateLimitExceeded exception into a clean 429 response."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,                 # 429 = Too Many Requests
        content={"detail": f"Rate limit exceeded: {exc.detail}"},         # Include which limit was hit
    )


app.add_middleware(SlowAPIMiddleware)  # Enforces default_limits from the Limiter on every route automatically

# --- Custom middleware ("Middleware" topic) ---
app.add_middleware(CSRFMiddleware)     # Double-submit-cookie CSRF protection on all unsafe methods
app.add_middleware(TimingMiddleware)   # Adds X-Process-Time-Ms to every response

# --- CORS ("CORS" topic) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,     # Only these frontend origins may call the API from a browser
    allow_credentials=True,                          # Allow cookies (needed for the CSRF cookie) to be sent cross-origin
    allow_methods=["*"],                                # Allow all HTTP methods (GET/POST/PUT/PATCH/DELETE/etc.)
    allow_headers=["*"],                                   # Allow all request headers (including X-CSRF-Token)
)

# --- Register custom exception handlers ("Handling Errors" topic) ---
register_exception_handlers(app)  # Wires up DuplicateEmailError -> 409 JSON response, etc.

# --- Include every router ("Bigger Applications - Multiple Files" topic) ---
app.include_router(auth.router)                          # /auth/token
app.include_router(candidate_info.router)                    # /candidates ...
app.include_router(candidate_education.router)                  # /candidates/{id}/education ...
app.include_router(candidate_work_experience.router)               # /candidates/{id}/work-experience ...
app.include_router(candidate_projects.router)                         # /candidates/{id}/projects ...
app.include_router(candidate_preferences.router)                         # /candidates/{id}/preferences ...


@app.on_event("startup")
def on_startup() -> None:
    """Creates all tables on startup if they don't already exist (fine for dev; use Alembic migrations in production)."""
    Base.metadata.create_all(bind=engine)  # Issues CREATE TABLE IF NOT EXISTS for every model registered on Base


@app.get("/health", tags=["Health"], summary="Liveness/health check")
async def health_check():
    """Simple endpoint for load balancers/uptime checks - deliberately outside the rate limiter's default scope."""
    return {"status": "ok"}  # Minimal payload confirming the app is up
