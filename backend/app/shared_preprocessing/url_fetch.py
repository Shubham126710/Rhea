"""
SSRF-safe URL fetching (Architecture.md §6.7, Rules.md §6).

Two layers of defense, deliberately combined:

1. Pre-flight validation: before any connection is made, the hostname
   is resolved via socket.getaddrinfo() and every returned address is
   checked against a denylist of private/loopback/link-local/
   multicast/reserved ranges (ipaddress.IPv4Address/IPv6Address's own
   classification, IPv4 and IPv6 both). Any disallowed address blocks
   the whole hostname for this hop.

2. Connection pinning: httpx is then told to connect directly to the
   already-validated IP address (not the hostname), while still
   sending the original Host header and TLS SNI hostname (via httpx's
   `extensions={"sni_hostname": ...}`, its documented mechanism for
   this). This closes the TOCTOU/DNS-rebinding gap that pre-flight
   validation alone leaves open: without pinning, nothing stops the
   name resolving to a *different* (internal) address by the time
   httpx makes its own connection a moment later.

Redirects are followed manually (`follow_redirects=False` on the
client) specifically so each hop re-enters this same validate-then-pin
path — a redirect to an internal address is blocked exactly like a
direct request to one would be. This is the "per-redirect-hop
revalidation" the approved plan calls for.
"""
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from app.core.config import get_settings
from app.shared_preprocessing.exceptions import (
    InvalidURL,
    ResponseTooLarge,
    SSRFBlocked,
    URLFetchFailed,
)

_ALLOWED_SCHEMES = ("http", "https")
_REDIRECT_STATUS_CODES = (301, 302, 303, 307, 308)

_USER_AGENT = "PropagateBot/1.0 (+shared-preprocessing; SSRF-guarded fetcher)"


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """RFC1918/loopback/link-local per Architecture.md §6.7, plus the
    other non-public ranges Python's ipaddress module classifies
    (multicast, reserved, unspecified) as defense in depth — a cloud
    metadata endpoint like 169.254.169.254 is link-local and is caught
    here."""
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_safe_ip(hostname: str, port: int) -> str:
    """Resolves hostname and returns one validated-safe IP literal to
    connect to. Blocks if ANY resolved address is disallowed (not just
    the first one) — a hostname that resolves to a mix of public and
    internal addresses is treated as untrustworthy for this request."""
    try:
        addrinfo = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise URLFetchFailed(f"DNS resolution failed for host {hostname!r}: {exc}") from exc
    if not addrinfo:
        raise URLFetchFailed(f"DNS resolution returned no addresses for host {hostname!r}")

    resolved_ips: list[str] = []
    for info in addrinfo:
        raw_ip = info[4][0]
        ip_str = raw_ip.split("%")[0]  # strip IPv6 zone id, e.g. fe80::1%eth0
        ip_obj = ipaddress.ip_address(ip_str)
        if _is_blocked_ip(ip_obj):
            raise SSRFBlocked(
                f"Host {hostname!r} resolved to {ip_str}, which is in a disallowed range"
            )
        resolved_ips.append(ip_str)
    return resolved_ips[0]


@dataclass(frozen=True)
class _HopResult:
    status_code: int
    headers: httpx.Headers
    body: bytes


def _fetch_one_hop(
    url: str,
    *,
    timeout: float,
    max_bytes: int,
    transport: httpx.BaseTransport | None,
) -> _HopResult:
    parsed = urlsplit(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise InvalidURL(f"Unsupported URL scheme: {parsed.scheme!r}")
    hostname = parsed.hostname
    if not hostname:
        raise InvalidURL(f"URL has no hostname: {url!r}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    safe_ip = _resolve_safe_ip(hostname, port)
    ip_for_url = f"[{safe_ip}]" if ":" in safe_ip else safe_ip
    pinned_url = urlunsplit(
        (parsed.scheme, f"{ip_for_url}:{port}", parsed.path or "/", parsed.query, "")
    )

    headers = {"Host": hostname, "User-Agent": _USER_AGENT}
    extensions = {"sni_hostname": hostname} if parsed.scheme == "https" else {}

    try:
        with httpx.Client(
            timeout=timeout, follow_redirects=False, transport=transport
        ) as client, client.stream(
            "GET", pinned_url, headers=headers, extensions=extensions
        ) as response:
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise ResponseTooLarge(
                        f"Response from {hostname!r} exceeded {max_bytes} byte limit"
                    )
            return _HopResult(response.status_code, response.headers, bytes(body))
    except httpx.TimeoutException as exc:
        raise URLFetchFailed(f"Timed out fetching {url!r}: {exc}") from exc
    except httpx.RequestError as exc:
        raise URLFetchFailed(f"Failed to fetch {url!r}: {exc}") from exc


def fetch_and_extract(
    url: str,
    *,
    transport: httpx.BaseTransport | None = None,
) -> tuple[str, bytes, str]:
    """Fetches `url`, following redirects manually with independent
    SSRF revalidation on every hop. Returns (final_url, body_bytes,
    content_type). `transport` is exposed only for tests (httpx's
    MockTransport) — production callers never pass it."""
    settings = get_settings()
    timeout = settings.PREPROCESSING_URL_FETCH_TIMEOUT_SECONDS
    max_redirects = settings.PREPROCESSING_URL_FETCH_MAX_REDIRECTS
    max_bytes = settings.PREPROCESSING_URL_FETCH_MAX_BYTES

    current_url = url
    for _ in range(max_redirects + 1):
        hop = _fetch_one_hop(
            current_url, timeout=timeout, max_bytes=max_bytes, transport=transport
        )
        if hop.status_code in _REDIRECT_STATUS_CODES:
            location = hop.headers.get("location")
            if not location:
                raise URLFetchFailed(
                    f"Redirect ({hop.status_code}) from {current_url!r} had no Location header"
                )
            current_url = urljoin(current_url, location)
            continue
        if not (200 <= hop.status_code < 300):
            raise URLFetchFailed(f"Fetch of {current_url!r} failed with status {hop.status_code}")
        content_type = hop.headers.get("content-type", "")
        return current_url, hop.body, content_type

    raise URLFetchFailed(f"Exceeded {max_redirects} redirects starting from {url!r}")
