"""
Entry points into the shared preprocessing pipeline.

Architecture.md §2 describes two entry points (offline dataset,
online submission); Phase 2's scope is the three ways *content*
reaches either entry point (pasted text, URL, file upload). All three
converge on the same canonicalize() + compute_content_hash() core
(normalization.py) — that convergence is what makes the exit gate
(identical content_hash for the same article via all three paths)
possible, and it's the thing Rules.md §2 ("preprocessing is one
codebase") is actually protecting.

No DB writes, no ML-facing code, no submission endpoint here — per the
approved Phase 2 plan, this module returns data to its caller and
stops.
"""
from dataclasses import dataclass

from app.shared_preprocessing.exceptions import ExtractionFailed
from app.shared_preprocessing.extraction import (
    extract_html_text,
    extract_pdf_text,
    extract_txt_text,
)
from app.shared_preprocessing.file_validation import validate_upload
from app.shared_preprocessing.normalization import canonicalize, compute_content_hash
from app.shared_preprocessing.url_fetch import fetch_and_extract


@dataclass(frozen=True)
class PreprocessedContent:
    canonical_text: str
    content_hash: str


def _finalize(text: str, *, empty_message: str) -> PreprocessedContent:
    canonical = canonicalize(text)
    if not canonical:
        raise ExtractionFailed(empty_message)
    return PreprocessedContent(canonical, compute_content_hash(canonical))


def preprocess_pasted_text(raw_text: str) -> PreprocessedContent:
    if raw_text is None or not raw_text.strip():
        raise ExtractionFailed("Pasted text is empty")
    return _finalize(raw_text, empty_message="Pasted text has no content after normalization")


def preprocess_url(url: str) -> PreprocessedContent:
    _final_url, body, content_type = fetch_and_extract(url)
    text = extract_html_text(body, content_type)
    return _finalize(text, empty_message="Fetched URL has no content after normalization")


def preprocess_file(filename: str, content: bytes, content_type: str | None) -> PreprocessedContent:
    kind = validate_upload(filename, content_type, content)
    text = extract_txt_text(content) if kind == "txt" else extract_pdf_text(content)
    return _finalize(text, empty_message="Uploaded file has no content after normalization")
