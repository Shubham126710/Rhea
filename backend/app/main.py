"""
FastAPI application entrypoint.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.security_headers import SecurityHeadersMiddleware

settings = get_settings()

app = FastAPI(title="Propagate API")

# Phase 9 / Architecture.md §8: CSP, HSTS (production only), X-Content-
# Type-Options, Referrer-Policy, frame-ancestors -- none of these
# existed anywhere in the app before Phase 9. Added before CORS so it
# runs on every response, including CORS-preflight and error
# responses, not just successful API calls.
app.add_middleware(SecurityHeadersMiddleware, settings=settings)

# Architecture.md §8: CORS restricted to production frontend origin +
# local dev origins, never a wildcard with credentials.
# Architecture.md §8: CORS restricted to production frontend origin +
# local dev origins, never a wildcard with credentials. That
# restriction is about origins specifically; methods/headers were
# previously wildcarded too, which wasn't wrong per the letter of §8
# but wasn't examined either. Narrowed here to exactly what the
# current API surface uses, since a credentialed CORS policy that's
# explicit about all three dimensions (origin, method, header) is the
# more defensible reading of "restricted," not just origin-restricted
# with everything else left open. Extend this list when a real new
# method/header is needed — not preemptively.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(api_v1_router)
