"""
Application configuration.

Source of truth for env-driven settings. Nothing here invents new
config surface beyond what Phase 0 needs: DB connectivity, Redis
connectivity (provisioned but not yet consumed by app code — see
PHASE0_SETUP.md), and CORS origins (Architecture.md §8).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+psycopg://propagate:propagate@localhost:5432/propagate"

    # Provisioned per Architecture.md §1/§3 (Redis: cache, rate limit,
    # jobs). Not consumed by any application code path yet — first
    # real usage arrives in Phase 5/6 (rate limiting, job queue,
    # explanation caching). Kept here now only so the setting exists
    # once and doesn't get re-invented later.
    REDIS_URL: str = "redis://localhost:6379/0"

    # Architecture.md §8: CORS restricted to the Netlify production
    # origin + localhost dev origins, never a wildcard with
    # credentials. Comma-separated list via env in real deployments.
    # Both localhost and 127.0.0.1 dev origins are listed explicitly --
    # browsers treat them as distinct origins for CORS purposes even
    # though they resolve to the same machine, so a frontend served
    # from either one needs its own entry here (Starlette's
    # CORSMiddleware returns 400 on preflight for any origin not in
    # this exact list).
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

    # --- Phase 1 (Auth) settings — PRD Batch B / Architecture.md §4/§6 ---

    # Server-managed session lifetime. Not numerically pinned by PRD/
    # Architecture beyond "deferred to Architecture.md"; these are the
    # values actually used, kept as named config rather than a magic
    # number in service.py so they're the one place to change.
    SESSION_TTL_HOURS: int = 12
    SESSION_REMEMBER_TTL_DAYS: int = 30

    SESSION_COOKIE_NAME: str = "propagate_session"

    # PRD Batch B: "after 5 failed attempts, throttle for ~20 minutes."
    FAILED_LOGIN_MAX_ATTEMPTS: int = 5
    FAILED_LOGIN_WINDOW_MINUTES: int = 20

    # PRD Batch B: password reset tokens are short-lived, single-use.
    PASSWORD_RESET_TTL_MINUTES: int = 30

    # Public origin the frontend SPA is served from — needed to build
    # any link the backend sends a user (currently: the password-reset
    # link). Bug found in audit: the reset endpoint was building this
    # link from the *backend's own* request.base_url, which pointed
    # the link at the API host (e.g. the Render backend), not the SPA
    # (Netlify). Distinct from CORS_ALLOWED_ORIGINS, which is a list
    # for the CORS middleware — this is a single value for constructing
    # outbound links.
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    # --- Phase 2 (Shared Preprocessing) settings — Architecture.md §4/§6.7/§8,
    # Rules.md §4/§6 ---

    # Rules.md §4: any code change to preprocessing logic bumps this. Not yet
    # persisted anywhere (analyses.preprocessing_version is written by Analysis
    # Orchestration in Phase 5) — defined here now so the string exists once,
    # in the module that owns the logic it versions, before it's needed.
    PREPROCESSING_VERSION: str = "1.0.0"

    # PRD §Security: file-size limits on uploads. Applied before any parsing
    # library touches the bytes (Rules.md §6).
    PREPROCESSING_MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024

    # Architecture.md §6.7: per-hop SSRF revalidation on URL fetch, bounded
    # timeout and redirect count so a slow/malicious host can't hang or loop
    # the worker indefinitely.
    PREPROCESSING_URL_FETCH_TIMEOUT_SECONDS: float = 10.0
    PREPROCESSING_URL_FETCH_MAX_REDIRECTS: int = 5

    # Cap on bytes read from a fetched URL response body, enforced while
    # streaming (not after buffering the whole thing) — a basic guard against
    # a malicious/misbehaving host sending an unbounded response.
    PREPROCESSING_URL_FETCH_MAX_BYTES: int = 10 * 1024 * 1024

    # PRD §Security: decompression-bomb protection. Applies to any extraction
    # source (PDF pages, fetched HTML) where a small input could expand into
    # an enormous amount of extracted text.
    PREPROCESSING_MAX_EXTRACTED_TEXT_CHARS: int = 2_000_000

    # --- Phase 5 (Analysis Orchestration) — Architecture.md §4/§6.1/§6.2/§6.3/§6.6 ---

    GRAPH_CONSTRUCTION_VERSION: str = "1.0.0"

    # Blocker 3 (blueprint §15): calibration_version has no home in
    # ArtifactManifest (Architecture §9 doesn't name it, Phase 3's
    # packaging.py has no such field). Resolution (b) from the
    # blueprint, adopted as the lower-disruption default: an
    # independently-versioned app-config value, analogous to
    # PREPROCESSING_VERSION, bumped whenever confidence-band
    # thresholding logic changes — zero changes to frozen Phase 3/4
    # code. Flagged for final confirmation, not silently decided.
    CALIBRATION_VERSION: str = "uncalibrated-1.0.0"

    # Which trained model artifact production loads. Rules.md §4: an
    # EXACT version, never implicit "latest". Empty by default — no
    # real trained artifact exists yet (Blocker 2) — submission fails
    # clearly rather than fabricating a verdict when unconfigured.
    ACTIVE_MODEL_VERSION: str = ""
    MODEL_ARTIFACT_DIR: str = ""
    MODEL_MANIFEST_PATH: str = ""

    RATE_LIMIT_ANALYSES_PER_HOUR: int = 20
    RATE_LIMIT_CONCURRENT_ANALYSES: int = 3

    GRAPH_MAX_NODES: int = 50

    # §3.6: config-tunable per Architecture §12, not hardcoded magic numbers.
    VISIBILITY_PERSONAL_MARKER_FIRST_PERSON_DENSITY: float = 0.02
    VISIBILITY_PERSONAL_MARKER_MIN_WORDS_FOR_CHECK: int = 20

    # --- Phase 6 (LLM Explanation Layer) — Architecture.md §3/§6.4/§6.6 ---

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-2.0-flash"
    LLM_MAX_TOKENS: int = 1024
    LLM_MAX_REGENERATION_ATTEMPTS: int = 2
    LLM_RATE_LIMIT_TOKENS_PER_DAY: int = 200_000


@lru_cache
def get_settings() -> Settings:
    return Settings()
