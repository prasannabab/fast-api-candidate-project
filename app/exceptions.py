"""
exceptions.py
--------------
Custom exception type + a registered exception handler, demonstrating the
FastAPI 'Handling Errors' tutorial topic (custom exception handlers, beyond
the built-in HTTPException).
"""

from fastapi import Request, status                 # Request object passed into handlers + status codes
from fastapi.responses import JSONResponse             # Used to build the error response body
from fastapi import FastAPI                               # Type hint for the app we register handlers on


class DuplicateEmailError(Exception):
    """Raised when trying to create a candidate whose email already exists."""

    def __init__(self, email: str):
        self.email = email  # Store the offending email so the handler can include it in the response
        super().__init__(f"A candidate with email '{email}' already exists")  # Standard Exception message


def register_exception_handlers(app: FastAPI) -> None:
    """Attaches all custom exception handlers to the given FastAPI app instance."""

    @app.exception_handler(DuplicateEmailError)  # Tells FastAPI: "whenever this exception is raised, use this handler"
    async def duplicate_email_handler(request: Request, exc: DuplicateEmailError) -> JSONResponse:
        """Turns a DuplicateEmailError into a clean 409 Conflict JSON response."""
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,                     # 409 = resource conflict (duplicate unique field)
            content={"detail": f"Email '{exc.email}' is already registered"},  # Client-friendly error payload
        )
