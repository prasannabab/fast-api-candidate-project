# fast-api-candidate-project
# Candidate Management API

A FastAPI + SQLAlchemy + PostgreSQL CRUD API for five candidate entities:
`CandidateInfo`, `CandidateEducation`, `CandidateWorkExperience`,
`CandidateProject`, `CandidatePreferences`.

## 1. Setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # then edit .env with real secrets / DB URL

# Create a Postgres database that matches DATABASE_URL in .env, e.g.:
#   createdb candidate_db

uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive Swagger UI (auto-generated
from the code you're reading). http://localhost:8000/redoc gives the ReDoc view.

## 2. Auth

There's a demo login endpoint so the protected write endpoints have something to
authenticate against:

```bash
curl -X POST http://localhost:8000/auth/token \
  -d "username=prasanna&password=changeme123"
```

Copy the returned `access_token` and send it as `Authorization: Bearer <token>`
on POST/PUT/PATCH/DELETE requests. Swap the hard-coded check in
`app/routers/auth.py` for a real users table before shipping this anywhere real.

## 3. CSRF

The API uses the double-submit-cookie pattern (`app/middleware.py`). Any GET
request sets a `csrf_token` cookie; state-changing requests (POST/PUT/PATCH/DELETE)
must echo that same value back in an `X-CSRF-Token` header, or they get a 403.
A browser-based frontend would read the cookie with JS and attach the header
automatically on every mutating fetch/axios call.

## 4. Project layout

```
app/
  main.py                       # App wiring: CORS, middleware, routers, metadata, startup
  config.py                     # Centralized settings (env vars)
  database.py                   # SQLAlchemy engine/session/get_db
  models.py                     # SQLAlchemy ORM models (the 5 tables)
  security.py                   # JWT auth (OAuth2 password flow)
  rate_limiter.py               # slowapi Limiter instance
  middleware.py                 # CSRF + request-timing middleware
  dependencies.py               # Shared Depends() callables
  exceptions.py                 # Custom exception + handler (DuplicateEmailError)
  schemas/
    common.py                   # Pagination, query/header/cookie param models
    candidate_info.py           # Create/Update/Read/InDB schemas
    candidate_education.py
    candidate_work_experience.py
    candidate_projects.py
    candidate_preferences.py    # + CandidateFullProfile (nested response)
  routers/
    auth.py                     # POST /auth/token
    candidate_info.py           # /candidates CRUD + upload/stream/SSE/background task
    candidate_education.py      # /candidates/{id}/education CRUD
    candidate_work_experience.py# /candidates/{id}/work-experience CRUD
    candidate_projects.py       # /candidates/{id}/projects CRUD
    candidate_preferences.py    # /candidates/{id}/preferences CRUD (1:1)
tests/
  conftest.py                   # TestClient + isolated DB session fixtures
  test_candidate_info.py        # Example tests
```

## 5. Design principles (SOLID)

- **S**ingle Responsibility: config, DB session, security, rate limiting, CSRF,
  and each entity's schema/router each live in their own module.
- **O**pen/Closed: new entities are added by dropping in a new model + schema +
  router file, without touching existing ones.
- **L**iskov Substitution: `CandidateInfoRead`/`InDB` extend `CandidateInfoBase`
  and remain drop-in compatible wherever the base is expected.
- **I**nterface Segregation: `Create`/`Update`/`Read` schemas are separate so
  callers only see the fields relevant to that operation (e.g. `Update` schemas
  don't force clients to resend every field).
- **D**ependency Inversion: routers depend on `Depends(get_db)`,
  `Depends(get_candidate_or_404)`, `Depends(get_current_user)` - abstractions -
  rather than constructing sessions or checking tokens themselves.

## 6. FastAPI tutorial topics -> where they live

| Topic | File(s) |
|---|---|
| Path Parameters | `routers/candidate_info.py::get_candidate` |
| Path Parameters and Numeric Validations | `routers/candidate_info.py::get_top_candidates` (`Path(..., gt=0, le=100)`) |
| Query Parameters | `routers/candidate_education.py::list_education` |
| Query Parameters and String Validations | `schemas/common.py::CandidateQueryParams` (`min_length`/`max_length`) |
| Query Parameter Models | `schemas/common.py::CandidateQueryParams` |
| Request Body | every `Create`/`Update` schema used as a POST/PATCH body |
| Body - Multiple Parameters | `routers/candidate_education.py` (path + body + injected dependency together) |
| Body - Fields | `schemas/*.py` (`Field(..., min_length=..., description=...)`) |
| Body - Nested Models | `schemas/candidate_preferences.py::CandidateFullProfile` |
| Declare Request Example Data | `json_schema_extra={"example": {...}}` in each `*Create` schema |
| Extra Data Types | `EmailStr`, `HttpUrl`, `date`, `Decimal`, `UUID` throughout `schemas/` |
| Cookie Parameters | `dependencies.py::get_session_cookies` |
| Header Parameters | `dependencies.py::get_common_headers` |
| Cookie Parameter Models | `schemas/common.py::SessionCookies` |
| Header Parameter Models | `schemas/common.py::CommonHeaders` |
| Response Model - Return Type | `response_model=` on every route |
| Extra Models | `Base`/`Create`/`Update`/`Read`/`InDB` classes per entity |
| Response Status Code | `status_code=status.HTTP_201_CREATED` / `204` etc. |
| Form Data | `routers/auth.py::login_for_access_token` |
| Form Models | could be added the same way as `Form(...)` params; `note` in resume upload shows a single Form field |
| Request Files | `routers/candidate_info.py::upload_resume` |
| Request Forms and Files | `routers/candidate_info.py::upload_resume` (file + `note` form field together) |
| Handling Errors | `exceptions.py`, `main.py::rate_limit_handler` |
| Path Operation Configuration | `summary=`, `tags=`, `description=` on every route |
| JSON Compatible Encoder | `routers/candidate_info.py::update_candidate` and `stream_candidates` |
| Body - Updates | every `PATCH` endpoint (`model_dump(exclude_unset=True)`) |
| Dependencies | `dependencies.py`, used everywhere via `Depends(...)` |
| Security | `security.py`, `routers/auth.py`, `Depends(get_current_user)` |
| Middleware | `middleware.py` (`CSRFMiddleware`, `TimingMiddleware`) |
| CORS | `main.py` (`CORSMiddleware`) |
| SQL (Relational) Databases | `database.py`, `models.py` |
| Bigger Applications - Multiple Files | `main.py` including every `routers/*.py` |
| Stream JSON Lines | `routers/candidate_info.py::stream_candidates` |
| Server-Sent Events (SSE) | `routers/candidate_info.py::candidate_processing_events` |
| Background Tasks | `routers/candidate_info.py::create_candidate` |
| Metadata and Docs URLs | `main.py` (`FastAPI(title=..., openapi_tags=...)`) |
| Testing | `tests/conftest.py`, `tests/test_candidate_info.py` |

## 7. Rate limiting

`app/rate_limiter.py` configures a `slowapi.Limiter` keyed by client IP.
`SlowAPIMiddleware` enforces `settings.rate_limit_default` (`100/minute`) on
every route by default; individual routes (e.g. `/auth/token`) add a stricter
`@limiter.limit("5/minute")` on top.

## 8. Known simplifications (call these out if this is for an interview/portfolio)

- Auth uses one hard-coded demo account - swap for a real `users` table + hashed
  passwords (`security.py` already has `get_password_hash`/`verify_password`
  ready to use).
- No Alembic migrations wired up yet - `Base.metadata.create_all()` runs on
  startup for convenience; add Alembic before running this against a real
  production database.
- The uniqueness/counting logic in `list_candidates` loads all matching rows to
  count them; swap for a `SELECT COUNT(*)` if the table gets large.
