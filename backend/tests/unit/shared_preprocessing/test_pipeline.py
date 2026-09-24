import socket

import httpx
import pytest

from app.shared_preprocessing import pipeline
from app.shared_preprocessing.exceptions import (
    ExtractionFailed,
    FileTooLarge,
    MalformedFile,
    SSRFBlocked,
    UnsupportedFileType,
    URLFetchFailed,
)

_ARTICLE_TEXT = (
    "Scientists Confirm Water Found on Distant Exoplanet\n\n"
    "Researchers announced today that spectroscopic analysis of a "
    "planet 40 light-years away has revealed clear signs of water "
    "vapor in its atmosphere, a finding that could reshape the search "
    "for habitable worlds beyond our solar system."
)


def _html_wrapping(article_text: str) -> bytes:
    paragraphs = "".join(f"<p>{line}</p>" for line in article_text.split("\n") if line.strip())
    return (
        f"<html><head><title>Article</title></head><body><article>{paragraphs}"
        f"</article></body></html>"
    ).encode()


def _fake_getaddrinfo(host_to_ip: dict):
    def _fake(host, port, *args, **kwargs):
        if host not in host_to_ip:
            raise socket.gaierror(f"no such host: {host}")
        ip = host_to_ip[host]
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))]

    return _fake


class _FakeSettings:
    PREPROCESSING_URL_FETCH_TIMEOUT_SECONDS = 5.0
    PREPROCESSING_URL_FETCH_MAX_REDIRECTS = 5
    PREPROCESSING_URL_FETCH_MAX_BYTES = 10 * 1024 * 1024
    PREPROCESSING_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
    PREPROCESSING_MAX_EXTRACTED_TEXT_CHARS = 2_000_000


def test_identical_content_hash_across_paste_url_and_txt_upload(monkeypatch):
    from app.shared_preprocessing import url_fetch

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo({"news.test": "93.184.1.1"}))
    monkeypatch.setattr(url_fetch, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        "app.shared_preprocessing.extraction.get_settings", lambda: _FakeSettings()
    )
    monkeypatch.setattr(
        "app.shared_preprocessing.file_validation.get_settings", lambda: _FakeSettings()
    )

    html_body = _html_wrapping(_ARTICLE_TEXT)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, content=html_body)

    pasted = pipeline.preprocess_pasted_text(_ARTICLE_TEXT)

    # preprocess_url() itself takes no transport override (Analysis
    # Orchestration, its real caller, never needs to inject a fake
    # network) -- exercise the same two functions it composes
    # directly, with the network mocked, to get an equivalent
    # end-to-end result for comparison.
    from app.shared_preprocessing.extraction import extract_html_text
    from app.shared_preprocessing.url_fetch import fetch_and_extract

    _final_url, body, content_type = fetch_and_extract(
        "http://news.test/article", transport=httpx.MockTransport(handler)
    )
    fetched_text = extract_html_text(body, content_type)
    fetched = pipeline._finalize(fetched_text, empty_message="unreachable in this test")

    uploaded = pipeline.preprocess_file("article.txt", _ARTICLE_TEXT.encode("utf-8"), "text/plain")

    assert pasted.content_hash == fetched.content_hash == uploaded.content_hash
    assert pasted.canonical_text == fetched.canonical_text == uploaded.canonical_text


def test_preprocess_pasted_text_rejects_empty_input():
    with pytest.raises(ExtractionFailed):
        pipeline.preprocess_pasted_text("   \n\t  ")


def test_preprocess_file_propagates_validation_errors():
    with pytest.raises(UnsupportedFileType):
        pipeline.preprocess_file("article.docx", b"whatever", "application/msword")


def test_preprocess_file_propagates_malformed_pdf():
    with pytest.raises(MalformedFile):
        pipeline.preprocess_file("article.pdf", b"not a real pdf", "application/pdf")


def test_preprocess_file_propagates_oversized_upload(monkeypatch):
    monkeypatch.setattr(
        "app.shared_preprocessing.file_validation.get_settings",
        lambda: _FakeSettings(),
    )
    oversized = b"a" * (_FakeSettings.PREPROCESSING_MAX_UPLOAD_BYTES + 1)
    with pytest.raises(FileTooLarge):
        pipeline.preprocess_file("article.txt", oversized, "text/plain")


def test_preprocess_url_propagates_ssrf_block(monkeypatch):
    from app.shared_preprocessing import url_fetch

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo({"internal.test": "10.0.0.5"}))
    monkeypatch.setattr(url_fetch, "get_settings", lambda: _FakeSettings())

    with pytest.raises(SSRFBlocked):
        from app.shared_preprocessing.url_fetch import fetch_and_extract

        fetch_and_extract(
            "http://internal.test/",
            transport=httpx.MockTransport(
                lambda r: (_ for _ in ()).throw(AssertionError("must not reach network"))
            ),
        )


def test_preprocess_url_propagates_unreachable_url(monkeypatch):
    from app.shared_preprocessing import url_fetch

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo({}))
    monkeypatch.setattr(url_fetch, "get_settings", lambda: _FakeSettings())

    with pytest.raises(URLFetchFailed):
        from app.shared_preprocessing.url_fetch import fetch_and_extract

        fetch_and_extract(
            "http://does-not-resolve.test/",
            transport=httpx.MockTransport(
                lambda r: (_ for _ in ()).throw(AssertionError("must not reach network"))
            ),
        )
