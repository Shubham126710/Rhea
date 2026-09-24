"""
Shared Preprocessing module.

Responsibility (Architecture.md §2): a single codebase with two entry
points — offline (research dataset pipeline) and online (live
submission pipeline) — so preprocessing logic never drifts between
training and inference (Rules.md §2).

Phase 2 scope (Phases.md): content_hash canonicalization, and
extraction from the three input types (pasted text, URL, .txt/.pdf
upload) that feed either entry point. No DB writes, no submission
endpoint, no ML-facing code yet — those are later phases' scope.

Public API:
    preprocess_pasted_text(raw_text) -> PreprocessedContent
    preprocess_url(url) -> PreprocessedContent
    preprocess_file(filename, content, content_type) -> PreprocessedContent
    canonicalize(text) -> str
    compute_content_hash(canonical_text) -> str
    PREPROCESSING_VERSION
"""
from app.core.config import get_settings
from app.shared_preprocessing.exceptions import (
    ExtractedContentTooLarge,
    ExtractionFailed,
    FileTooLarge,
    InvalidURL,
    MalformedFile,
    PreprocessingError,
    ResponseTooLarge,
    SSRFBlocked,
    UnsupportedContentType,
    UnsupportedFileType,
    URLFetchFailed,
)
from app.shared_preprocessing.normalization import canonicalize, compute_content_hash
from app.shared_preprocessing.pipeline import (
    PreprocessedContent,
    preprocess_file,
    preprocess_pasted_text,
    preprocess_url,
)

PREPROCESSING_VERSION = get_settings().PREPROCESSING_VERSION

__all__ = [
    "PREPROCESSING_VERSION",
    "PreprocessedContent",
    "canonicalize",
    "compute_content_hash",
    "preprocess_pasted_text",
    "preprocess_url",
    "preprocess_file",
    "PreprocessingError",
    "ExtractionFailed",
    "ExtractedContentTooLarge",
    "InvalidURL",
    "URLFetchFailed",
    "SSRFBlocked",
    "UnsupportedContentType",
    "ResponseTooLarge",
    "UnsupportedFileType",
    "FileTooLarge",
    "MalformedFile",
]
