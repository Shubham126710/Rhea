import io

import pytest
from reportlab.pdfgen import canvas

from app.shared_preprocessing.exceptions import (
    ExtractionFailed,
    MalformedFile,
    UnsupportedContentType,
)
from app.shared_preprocessing.extraction import (
    extract_html_text,
    extract_pdf_text,
    extract_txt_text,
)


def _make_pdf_bytes(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, text)
    c.save()
    return buf.getvalue()


def test_extract_txt_text_happy_path():
    assert extract_txt_text(b"Hello, world!") == "Hello, world!"


def test_extract_txt_text_rejects_invalid_utf8():
    with pytest.raises(MalformedFile):
        extract_txt_text(b"\xff\xfe not valid utf-8 \x80\x81")


def test_extract_txt_text_rejects_whitespace_only():
    with pytest.raises(ExtractionFailed):
        extract_txt_text(b"   \n\t  ")


def test_extract_pdf_text_happy_path():
    pdf_bytes = _make_pdf_bytes("The quick brown fox jumps over the lazy dog.")
    text = extract_pdf_text(pdf_bytes)
    assert "quick brown fox" in text


def test_extract_pdf_text_rejects_corrupt_pdf_that_passed_magic_byte_check():
    # Has the %PDF- header (so file_validation would accept it) but is
    # truncated/corrupt beyond that — must be caught here, not crash.
    corrupt = b"%PDF-1.4\n%garbage not a real pdf structure at all"
    with pytest.raises(MalformedFile):
        extract_pdf_text(corrupt)


def test_extract_pdf_text_rejects_blank_page_as_extraction_failed():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.save()  # one blank page, no text drawn
    with pytest.raises(ExtractionFailed):
        extract_pdf_text(buf.getvalue())


def test_extract_html_text_happy_path():
    html = (
        b"<html><head><title>T</title></head><body><article>"
        b"<h1>Headline</h1><p>This is the first paragraph of a real "
        b"article with enough content for trafilatura to extract "
        b"reliably as the main body text of the page.</p>"
        b"<p>And a second paragraph to make it look like a genuine "
        b"article rather than a stub, since extractors favor pages "
        b"with substantial body content.</p>"
        b"</article></body></html>"
    )
    text = extract_html_text(html, "text/html; charset=utf-8")
    assert "first paragraph" in text


def test_extract_html_text_rejects_non_html_content_type():
    with pytest.raises(UnsupportedContentType):
        extract_html_text(b"\x89PNG\r\n...", "image/png")


def test_extract_html_text_plain_text_content_type_passthrough():
    text = extract_html_text(b"Just plain text content here.", "text/plain")
    assert text == "Just plain text content here."


def test_extract_html_text_rejects_empty_extraction():
    html = b"<html><body></body></html>"
    with pytest.raises(ExtractionFailed):
        extract_html_text(html, "text/html")
