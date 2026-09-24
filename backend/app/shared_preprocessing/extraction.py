"""
Extraction: turns raw bytes from any of the three input sources into
plain text, ready for normalization.canonicalize(). Pasted text needs
no extraction step (it already is text) and is handled directly in
pipeline.py.

Rules.md §6: file extraction functions here are only ever called after
file_validation.validate_upload() has already accepted the bytes —
this module does not re-validate.
"""
import io

import pypdf
import trafilatura
from pypdf.errors import PdfReadError

from app.core.config import get_settings
from app.shared_preprocessing.exceptions import (
    ExtractedContentTooLarge,
    ExtractionFailed,
    MalformedFile,
    UnsupportedContentType,
)

_HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml")
_PLAIN_TEXT_CONTENT_TYPES = ("text/plain",)


def extract_html_text(body: bytes, content_type: str) -> str:
    """Extracts article text from a fetched URL response. content_type
    is the response's Content-Type header (as returned by url_fetch) —
    checked before trafilatura ever touches the body."""
    mime = content_type.split(";")[0].strip().lower()
    if mime not in _HTML_CONTENT_TYPES + _PLAIN_TEXT_CONTENT_TYPES:
        raise UnsupportedContentType(f"Cannot extract text from content type {content_type!r}")

    html_str = body.decode("utf-8", errors="replace")

    if mime in _PLAIN_TEXT_CONTENT_TYPES:
        text = html_str
    else:
        text = trafilatura.extract(html_str, favor_recall=True) or ""

    if not text.strip():
        raise ExtractionFailed("Fetched URL produced no extractable text content")

    settings = get_settings()
    if len(text) > settings.PREPROCESSING_MAX_EXTRACTED_TEXT_CHARS:
        raise ExtractedContentTooLarge(
            f"Extracted text from URL exceeded "
            f"{settings.PREPROCESSING_MAX_EXTRACTED_TEXT_CHARS} characters"
        )
    return text


def extract_txt_text(content: bytes) -> str:
    """content has already passed file_validation.validate_upload()
    (size, extension, declared MIME, null-byte check)."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MalformedFile(f"File is not valid UTF-8 text: {exc}") from exc

    if not text.strip():
        raise ExtractionFailed("Uploaded .txt file has no extractable text")
    return text


def extract_pdf_text(content: bytes) -> str:
    """content has already passed file_validation.validate_upload()
    (size, extension, declared MIME, %PDF- magic-byte check). pypdf is
    a third-party parser operating on untrusted bytes whose failure
    modes for malformed PDFs are not fully enumerable in advance
    (corrupt xref tables, truncated streams, etc. surface as a mix of
    pypdf's own errors and stdlib ValueError/TypeError/IndexError from
    its internal parsing) — caught broadly here, at this single
    boundary, and converted to MalformedFile rather than left to crash
    the caller. This is the parsing step; structural validation
    already happened in file_validation before this function is ever
    called."""
    settings = get_settings()
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise MalformedFile("PDF is password-protected/encrypted")

        pages_text: list[str] = []
        total_chars = 0
        for page in reader.pages:
            page_text = page.extract_text() or ""
            total_chars += len(page_text)
            if total_chars > settings.PREPROCESSING_MAX_EXTRACTED_TEXT_CHARS:
                raise ExtractedContentTooLarge(
                    f"Extracted text from PDF exceeded "
                    f"{settings.PREPROCESSING_MAX_EXTRACTED_TEXT_CHARS} characters"
                )
            pages_text.append(page_text)
        text = "\n".join(pages_text)
    except (MalformedFile, ExtractedContentTooLarge):
        raise
    except (PdfReadError, ValueError, TypeError, KeyError, IndexError) as exc:
        raise MalformedFile(f"Failed to parse PDF: {exc}") from exc

    if not text.strip():
        raise ExtractionFailed("Uploaded PDF has no extractable text")
    return text
