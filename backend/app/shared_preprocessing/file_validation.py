"""
Upload validation for .txt/.pdf files (Phases.md Phase 2 scope,
Rules.md §6: "Every uploaded file goes through MIME/size/structure
validation before touching any parsing library — no parsing-then-
validating").

validate_upload() is the only function in this module and it is a
pure gate: it either returns which kind of file this is ("txt" or
"pdf") or raises. Nothing here calls pypdf or decodes the file as
text — that's extraction.py's job, and it only runs after this
function has already accepted the bytes.
"""
from pathlib import Path

from app.core.config import get_settings
from app.shared_preprocessing.exceptions import (
    FileTooLarge,
    MalformedFile,
    UnsupportedFileType,
)

# extension -> expected declared content-type (Phases.md Phase 2 scope:
# .txt/.pdf only)
_ALLOWED_UPLOADS = {
    ".txt": "text/plain",
    ".pdf": "application/pdf",
}

_PDF_MAGIC = b"%PDF-"


def validate_upload(filename: str, content_type: str | None, content: bytes) -> str:
    """Returns "txt" or "pdf". Raises FileTooLarge, UnsupportedFileType,
    or MalformedFile without ever handing `content` to a parser."""
    settings = get_settings()

    if len(content) == 0:
        raise MalformedFile("Uploaded file is empty")

    if len(content) > settings.PREPROCESSING_MAX_UPLOAD_BYTES:
        raise FileTooLarge(
            f"Uploaded file ({len(content)} bytes) exceeds the "
            f"{settings.PREPROCESSING_MAX_UPLOAD_BYTES} byte limit"
        )

    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_UPLOADS:
        raise UnsupportedFileType(
            f"Unsupported file extension {ext!r}; allowed: {sorted(_ALLOWED_UPLOADS)}"
        )

    expected_content_type = _ALLOWED_UPLOADS[ext]
    if content_type:
        declared_mime = content_type.split(";")[0].strip().lower()
        if declared_mime != expected_content_type:
            raise UnsupportedFileType(
                f"Declared content-type {content_type!r} does not match "
                f"extension {ext!r} (expected {expected_content_type!r})"
            )

    if ext == ".pdf":
        if not content.startswith(_PDF_MAGIC):
            raise MalformedFile("File does not start with the PDF magic bytes (%PDF-)")
        return "pdf"

    # .txt: reject binary data masquerading as text before we ever try
    # to decode it in extraction.py
    if b"\x00" in content:
        raise MalformedFile("File contains null bytes; not valid text")
    return "txt"
