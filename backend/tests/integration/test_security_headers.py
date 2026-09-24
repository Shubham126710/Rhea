"""Phase 9 / Architecture.md §8: security response headers."""


def test_security_headers_present_on_every_response(client):
    response = client.get("/api/v1/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_security_headers_present_on_error_responses_too(client):
    response = client.get("/api/v1/analyses/not-a-valid-uuid")
    assert response.status_code >= 400
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_hsts_absent_in_development_environment(client):
    # conftest's test settings run with ENVIRONMENT=development (or
    # unset, defaulting to it) -- sending HSTS over what's actually a
    # plain-HTTP test client would be the wrong behavior, not just an
    # untested one.
    response = client.get("/api/v1/health")
    assert "Strict-Transport-Security" not in response.headers
