"""
security.py
------------
Implements the FastAPI 'Security' tutorial pattern: OAuth2 password-bearer flow
with JWT access tokens. Every mutating endpoint depends on `get_current_user`
so unauthenticated callers get a clean 401.
"""

from datetime import datetime, timedelta, timezone       # Used to compute token expiry
from typing import Any                                     # Generic typing for the decoded payload

from fastapi import Depends, HTTPException, status          # Dependency injection + error helpers
from fastapi.security import OAuth2PasswordBearer             # Standard "Bearer <token>" auth scheme
from jose import jwt, JWTError                                  # JWT encode/decode + its exception type
from passlib.context import CryptContext                          # Password hashing helper

from app.config import settings  # Centralized settings (JWT secret/algorithm/expiry)

# Tells FastAPI/Swagger where clients should POST username+password to get a token.
# This also makes the "Authorize" button appear in the interactive docs.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Password hashing context (bcrypt) - used if/when we add real user signup/login.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)  # Delegates to passlib's constant-time comparison


def get_password_hash(password: str) -> str:
    """Hashes a plaintext password for storage."""
    return pwd_context.hash(password)  # Produces a salted bcrypt hash


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Builds a signed JWT access token for the given subject (typically a user id/email)."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)  # Default expiry from settings
    )
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire}          # Standard JWT claims: subject + expiry
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)  # Sign the token


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodes & verifies a JWT, raising a 401 HTTPException if it's invalid/expired."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])  # Verify signature + expiry
    except JWTError:  # Covers expired tokens, bad signatures, malformed tokens, etc.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,     # Standard "not authenticated" status code
            detail="Could not validate credentials",         # Generic message (don't leak internals)
            headers={"WWW-Authenticate": "Bearer"},             # Tells the client which auth scheme to use
        )


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    FastAPI dependency: extracts the bearer token, validates it, and returns the
    subject (user identifier). Add `Depends(get_current_user)` to any route that
    should require authentication.
    """
    payload = decode_access_token(token)          # Decode & verify the incoming JWT
    subject = payload.get("sub")                     # Pull the "subject" claim (who the token belongs to)
    if subject is None:                                 # Defensive check in case of a malformed-but-valid-signature token
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return subject  # Routers can use this string (e.g. as an audit "created_by" value)
