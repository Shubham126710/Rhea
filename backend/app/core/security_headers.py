"""
Security response headers — Architecture.md §8: "HTTPS enforced,
secure/HttpOnly/SameSite cookies, CSP, HSTS, X-Content-Type-Options,
Referrer-Policy, frame-ancestors protection." Cookies (secure/
HttpOnly/SameSite) are already set where sessions are issued (Phase
1, app/auth) — this middleware covers the remaining response-header
items, none of which existed anywhere in the app before Phase 9.

HSTS is gated to ENVIRONMENT == "production": sending
Strict-Transport-Security over a plain-HTTP local/dev connection is
not just inert, it actively risks locking a developer's browser into
HTTPS-only for the dev host. The rest apply unconditionally since
they're safe (and meaningful) in any environment.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: Settings):
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # frame-ancestors 'none': this is an API backend with no
        # legitimate reason to be framed (Architecture.md §8's "frame-
        # ancestors protection"); default-src 'none' since the API
        # itself never serves HTML/JS for a browser to execute.
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if self._settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
