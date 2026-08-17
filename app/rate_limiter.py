"""
rate_limiter.py
-----------------
Central place that configures rate limiting (via slowapi, a Starlette/FastAPI
wrapper around the `limits` library). Imported by main.py (to register the
exception handler + middleware) and by every router (to decorate endpoints).
"""

from slowapi import Limiter                        # Core rate-limiter object
from slowapi.util import get_remote_address           # Default "identify the caller" strategy (by IP)

from app.config import settings  # Pulls the default rate limit string, e.g. "100/minute"

# One shared Limiter instance for the whole app.
# key_func=get_remote_address means limits are applied per client IP address;
# in production behind a load balancer you'd swap this for a function that reads
# X-Forwarded-For, or rate-limit per authenticated user id instead.
limiter = Limiter(
    key_func=get_remote_address,                  # How to identify "who" is making the request
    default_limits=[settings.rate_limit_default],   # Fallback limit applied if a route has no explicit @limiter.limit(...)
)
