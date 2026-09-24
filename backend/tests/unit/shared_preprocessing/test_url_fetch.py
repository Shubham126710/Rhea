import socket

import httpx
import pytest

from app.shared_preprocessing import url_fetch
from app.shared_preprocessing.exceptions import (
    InvalidURL,
    ResponseTooLarge,
    SSRFBlocked,
    URLFetchFailed,
)
from app.shared_preprocessing.url_fetch import fetch_and_extract


def _fake_getaddrinfo(host_to_ip: dict):
    def _fake(host, port, *args, **kwargs):
        if host not in host_to_ip:
            raise socket.gaierror(f"no such host: {host}")
        ip = host_to_ip[host]
        if ":" in ip:
            return [(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port, 0, 0))]
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))]

    return _fake


class _FakeSettings:
    PREPROCESSING_URL_FETCH_TIMEOUT_SECONDS = 5.0
    PREPROCESSING_URL_FETCH_MAX_REDIRECTS = 5
    PREPROCESSING_URL_FETCH_MAX_BYTES = 10 * 1024 * 1024


def _install_fake_settings(monkeypatch, **overrides):
    settings = _FakeSettings()
    for key, value in overrides.items():
        setattr(settings, key, value)
    monkeypatch.setattr(url_fetch, "get_settings", lambda: settings)
    return settings


def test_public_ip_allowed_and_pinned(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo({"example.com": "93.184.216.34"}))
    _install_fake_settings(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "93.184.216.34"  # pinned, not re-resolved
        assert request.headers["host"] == "example.com"  # original Host preserved
        assert request.extensions.get("sni_hostname") == "example.com"
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"hello")

    final_url, body, content_type = fetch_and_extract(
        "https://example.com/article", transport=httpx.MockTransport(handler)
    )
    assert final_url == "https://example.com/article"
    assert body == b"hello"
    assert content_type == "text/html"


@pytest.mark.parametrize(
    "hostname,ip",
    [
        ("loopback.test", "127.0.0.1"),
        ("rfc1918-a.test", "10.0.0.5"),
        ("rfc1918-b.test", "172.16.0.5"),
        ("rfc1918-c.test", "192.168.1.5"),
        ("link-local.test", "169.254.169.254"),  # cloud metadata endpoint
        ("ipv6-loopback.test", "::1"),
        ("ipv6-ula.test", "fd00::1"),
    ],
)
def test_disallowed_ranges_blocked_without_any_network_call(monkeypatch, hostname, ip):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo({hostname: ip}))
    _install_fake_settings(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network layer must never be reached for a blocked IP")

    with pytest.raises(SSRFBlocked):
        fetch_and_extract(f"http://{hostname}/", transport=httpx.MockTransport(handler))


def test_redirect_hop_to_internal_target_is_blocked(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        _fake_getaddrinfo({"safe.test": "93.184.216.34", "internal.test": "10.1.1.1"}),
    )
    _install_fake_settings(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["host"] == "safe.test"  # only the safe hop should ever connect
        return httpx.Response(302, headers={"location": "http://internal.test/secret"})

    with pytest.raises(SSRFBlocked):
        fetch_and_extract("http://safe.test/start", transport=httpx.MockTransport(handler))


def test_redirect_chain_of_safe_hosts_succeeds(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        _fake_getaddrinfo({"hop1.test": "93.184.1.1", "hop2.test": "93.184.2.2"}),
    )
    _install_fake_settings(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.headers["host"]
        if host == "hop1.test":
            return httpx.Response(301, headers={"location": "http://hop2.test/final"})
        assert host == "hop2.test"
        return httpx.Response(200, headers={"content-type": "text/plain"}, content=b"final content")

    final_url, body, content_type = fetch_and_extract(
        "http://hop1.test/start", transport=httpx.MockTransport(handler)
    )
    assert final_url == "http://hop2.test/final"
    assert body == b"final content"


def test_exceeding_max_redirects_raises(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo({"loop.test": "93.184.1.1"}))
    _install_fake_settings(monkeypatch, PREPROCESSING_URL_FETCH_MAX_REDIRECTS=2)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://loop.test/again"})

    with pytest.raises(URLFetchFailed):
        fetch_and_extract("http://loop.test/start", transport=httpx.MockTransport(handler))


def test_dns_resolution_failure_raises_url_fetch_failed_not_ssrf_blocked(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo({}))
    _install_fake_settings(monkeypatch)

    with pytest.raises(URLFetchFailed):
        fetch_and_extract("http://does-not-resolve.test/", transport=httpx.MockTransport(
            lambda r: (_ for _ in ()).throw(AssertionError("should never reach network"))
        ))


def test_non_2xx_3xx_status_raises_url_fetch_failed(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo({"safe.test": "93.184.1.1"}))
    _install_fake_settings(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    with pytest.raises(URLFetchFailed):
        fetch_and_extract("http://safe.test/missing", transport=httpx.MockTransport(handler))


def test_oversized_response_rejected_while_streaming(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo({"safe.test": "93.184.1.1"}))
    _install_fake_settings(monkeypatch, PREPROCESSING_URL_FETCH_MAX_BYTES=10)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 1000)

    with pytest.raises(ResponseTooLarge):
        fetch_and_extract("http://safe.test/big", transport=httpx.MockTransport(handler))


def test_disallowed_scheme_rejected():
    with pytest.raises(InvalidURL):
        fetch_and_extract("ftp://example.com/file", transport=httpx.MockTransport(
            lambda r: (_ for _ in ()).throw(AssertionError("should never reach network"))
        ))


def test_url_with_no_hostname_rejected():
    with pytest.raises(InvalidURL):
        fetch_and_extract("http:///path-with-no-host", transport=httpx.MockTransport(
            lambda r: (_ for _ in ()).throw(AssertionError("should never reach network"))
        ))
