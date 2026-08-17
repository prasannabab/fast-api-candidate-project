"""
config.py
---------
Single Responsibility: this module's ONLY job is to load and expose configuration.
Nothing else in the app should read os.environ directly - they should import `settings`
from here. This keeps configuration centralized (easy to change/test) - part of SOLID's
Single Responsibility Principle (SRP).
"""

from functools import lru_cache               # Used to cache the Settings object (singleton-like behaviour)
from typing import List                        # Type hint for a list of strings

from pydantic_settings import BaseSettings, SettingsConfigDict  # Pydantic's env-var powered settings class


class Settings(BaseSettings):
    """
    Typed representation of every environment variable the app needs.
    Pydantic will validate types automatically (e.g. int fields must be ints).
    """

    # --- Database ---
    database_url: str = "postgresql://candidate_user:candidate_pass@localhost:5432/candidate_db"  # Postgres DSN

    # --- JWT / auth ---
    jwt_secret_key: str = "dev-secret-change-me"   # Key used to sign JWT tokens
    jwt_algorithm: str = "HS256"                    # Algorithm used to sign/verify JWTs
    access_token_expire_minutes: int = 60           # How long an access token stays valid

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"     # Comma-separated allowed origins, parsed below

    # --- CSRF ---
    csrf_secret_key: str = "dev-csrf-secret-change-me"  # Key used to sign the CSRF cookie

    # --- File uploads ---
    upload_dir: str = "./uploads"                    # Where resume files get stored on disk

    # --- Rate limiting ---
    rate_limit_default: str = "100/minute"            # Default rate limit applied to most endpoints

    # --- Metadata ---
    app_name: str = "Candidate Management API"        # Shown in OpenAPI docs
    app_version: str = "1.0.0"                          # Shown in OpenAPI docs

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")  # Tell pydantic to read a .env file

    @property
    def cors_origin_list(self) -> List[str]:
        """Splits the comma-separated cors_origins string into a clean Python list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]  # Strip whitespace, drop empties


@lru_cache()  # Cache so we only construct/parse Settings once per process (acts like a singleton)
def get_settings() -> Settings:
    """Dependency-friendly accessor for settings (importable & overridable in tests)."""
    return Settings()  # Instantiate Settings, which reads from environment/.env automatically


settings = get_settings()  # Module-level singleton other modules can `from app.config import settings`
