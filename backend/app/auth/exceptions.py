"""
Domain exceptions for the Auth service layer.

Kept separate from FastAPI's HTTPException (Rules.md §3.1 — single
responsibility: service.py expresses auth outcomes, api/v1/auth.py
is the only place that knows about HTTP status codes). This also
means service.py's unit tests don't need a FastAPI app at all.
"""


class InvalidCredentials(Exception):
    """Login failed. Deliberately used for BOTH 'no such user' and
    'wrong password' — the API layer must map this to one identical
    generic message either way (enumeration-safe, Master Build
    Batch P)."""


class AccountThrottled(Exception):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Too many failed login attempts")


class InvalidOrExpiredToken(Exception):
    """Raised for an unknown, expired, or already-used password-reset
    token."""


class SessionNotFound(Exception):
    """Raised when a session cookie doesn't match any live session."""
