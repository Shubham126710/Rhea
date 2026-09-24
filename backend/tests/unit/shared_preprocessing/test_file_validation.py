import pytest

from app.shared_preprocessing.exceptions import FileTooLarge, MalformedFile, UnsupportedFileType
from app.shared_preprocessing.file_validation import validate_upload


def test_valid_txt_accepted():
    assert validate_upload("article.txt", "text/plain", b"hello world") == "txt"


def test_valid_pdf_accepted():
    assert validate_upload("article.pdf", "application/pdf", b"%PDF-1.4\n...") == "pdf"


def test_content_type_omitted_falls_back_to_extension():
    assert validate_upload("article.txt", None, b"hello") == "txt"


def test_empty_file_rejected():
    with pytest.raises(MalformedFile):
        validate_upload("article.txt", "text/plain", b"")


def test_oversized_file_rejected_before_parsing():
    from app.core.config import get_settings

    limit = get_settings().PREPROCESSING_MAX_UPLOAD_BYTES
    oversized = b"a" * (limit + 1)
    with pytest.raises(FileTooLarge):
        validate_upload("article.txt", "text/plain", oversized)


def test_unsupported_extension_rejected():
    with pytest.raises(UnsupportedFileType):
        validate_upload("article.docx", "application/msword", b"whatever")


def test_mismatched_declared_content_type_rejected():
    with pytest.raises(UnsupportedFileType):
        validate_upload("article.txt", "application/pdf", b"hello")


def test_pdf_missing_magic_bytes_rejected_as_malformed():
    with pytest.raises(MalformedFile):
        validate_upload("article.pdf", "application/pdf", b"not actually a pdf")


def test_txt_with_null_bytes_rejected_as_malformed():
    with pytest.raises(MalformedFile):
        validate_upload("article.txt", "text/plain", b"hello\x00world")


def test_wrong_mime_and_oversized_upload_rejected_before_any_parsing():
    """Exit-gate case: 'oversized/wrong-MIME uploads rejected before
    parsing' — assert with a payload that would also fail to parse if
    it reached a parser, to confirm validation short-circuits first."""
    from app.core.config import get_settings

    limit = get_settings().PREPROCESSING_MAX_UPLOAD_BYTES
    garbage = b"\xff\xd8\xff" + b"a" * (limit + 1)  # JPEG-magic-bytes-prefixed, oversized
    with pytest.raises((FileTooLarge, UnsupportedFileType)):
        validate_upload("article.pdf", "image/jpeg", garbage)
