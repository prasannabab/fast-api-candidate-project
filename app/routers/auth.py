"""
auth.py (router)
------------------
Minimal login endpoint demonstrating 'Form Data' + 'Security' tutorial topics.
In a real system this would check a users table; here we check a single demo
account from settings so the rest of the CRUD API has something to authenticate
against, and so `get_current_user` has a real token to validate.
"""

from fastapi import APIRouter, Depends, HTTPException, status         # Router + DI + error helpers
from fastapi.security import OAuth2PasswordRequestForm                   # Parses standard "username"/"password" form fields

from app.security import create_access_token   # Builds the JWT returned to the client
from app.rate_limiter import limiter               # Shared rate limiter instance
from fastapi import Request                            # Needed because slowapi's decorator inspects the raw Request

router = APIRouter(prefix="/auth", tags=["Authentication"])  # All routes here live under /auth, grouped in docs under "Authentication"

# Hard-coded demo credentials - replace with a real users table lookup in production.
DEMO_USERNAME = "prasanna"
DEMO_PASSWORD = "changeme123"


@router.post(
    "/token",                                    # Matches the tokenUrl configured in security.py's OAuth2PasswordBearer
    summary="Obtain a JWT access token",           # "Path Operation Configuration": custom summary
    description="Exchange a username/password (Form Data) for a bearer access token.",  # Custom description
    response_description="A JWT access token",       # Custom response description
)
@limiter.limit("5/minute")  # Tight rate limit on login to slow down credential-stuffing attempts
async def login_for_access_token(
    request: Request,                                     # Required by slowapi's limiter decorator
    form_data: OAuth2PasswordRequestForm = Depends(),        # "Form Data": parses application/x-www-form-urlencoded body
):
    """Validates demo credentials and returns a signed JWT access token."""
    if form_data.username != DEMO_USERNAME or form_data.password != DEMO_PASSWORD:  # Naive credential check
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,          # Wrong credentials -> 401
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},               # Standard header hinting at the expected auth scheme
        )
    access_token = create_access_token(subject=form_data.username)  # Mint a signed JWT for this user
    return {"access_token": access_token, "token_type": "bearer"}      # Standard OAuth2 token response shape
