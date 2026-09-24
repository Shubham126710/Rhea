"""
Domain exceptions for the Shared Preprocessing module.

Kept separate from FastAPI's HTTPException, same reasoning as
auth/exceptions.py: this module has no HTTP layer of its own in
Phase 2 (no submission endpoint yet — Analysis Orchestration will be
the caller in a later phase and is responsible for mapping these to
whatever response it returns).
"""


class PreprocessingError(Exception):
    """Base class for every domain error this module raises."""


class ExtractionFailed(PreprocessingError):
    """Extraction ran but produced no usable text (empty/whitespace-only
    after normalization), for any input type."""


class ExtractedContentTooLarge(PreprocessingError):
    """Extracted text exceeded PREPROCESSING_MAX_EXTRACTED_TEXT_CHARS —
    decompression-bomb guard (PRD §Security)."""


# --- URL fetch (Architecture.md §6.7) ---


class InvalidURL(PreprocessingError):
    """The URL is malformed or uses a disallowed scheme."""


class URLFetchFailed(PreprocessingError):
    """DNS resolution, connection, timeout, or non-2xx/3xx HTTP failure.
    Distinct from SSRFBlocked: this is an ordinary "unreachable URL"
    case (PRD §4.3), not a security block."""


class SSRFBlocked(PreprocessingError):
    """A hostname (original or a redirect hop) resolved to an address
    in a disallowed range (Architecture.md §6.7)."""


class UnsupportedContentType(PreprocessingError):
    """The fetched response's Content-Type isn't one this module knows
    how to extract from."""


class ResponseTooLarge(PreprocessingError):
    """The fetched response body exceeded PREPROCESSING_URL_FETCH_MAX_BYTES."""


# --- File upload (Rules.md §6) ---


class UnsupportedFileType(PreprocessingError):
    """File extension or declared content-type isn't in the allowed set
    (.txt/.pdf per Phases.md Phase 2 scope)."""


class FileTooLarge(PreprocessingError):
    """File exceeded PREPROCESSING_MAX_UPLOAD_BYTES."""


class MalformedFile(PreprocessingError):
    """File failed structural validation (bad magic bytes, invalid
    encoding, unparseable PDF structure, etc.) — raised before or
    during parsing, never silently swallowed (Rules.md §3.2)."""
