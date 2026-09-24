from app.core.config import get_settings
from app.db.models.user import User


def _signup(client, email="alice@example.com", password="correct horse battery"):
    return client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Alice", "password": password},
    )


def test_signup_creates_a_real_user(client, db_session):
    response = _signup(client)
    assert response.status_code == 201
    user = db_session.query(User).filter(User.email == "alice@example.com").one()
    assert user.password_hash != "correct horse battery"  # never plaintext
    assert user.role == "user"


def test_signup_is_enumeration_safe_for_existing_email(client):
    first = _signup(client)
    second = _signup(client)  # same email again
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()  # identical response either way


def test_login_success_sets_httponly_secure_samesite_cookie(client):
    _signup(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "correct horse battery"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"

    settings = get_settings()
    set_cookie_header = response.headers.get("set-cookie", "")
    assert settings.SESSION_COOKIE_NAME in set_cookie_header
    assert "HttpOnly" in set_cookie_header
    assert "Secure" in set_cookie_header
    assert "SameSite=lax" in set_cookie_header


def test_login_wrong_password_and_nonexistent_email_give_identical_error(client):
    _signup(client)
    wrong_password = client.post(
        "/api/v1/auth/login", json={"email": "alice@example.com", "password": "nope"}
    )
    no_such_user = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "nope"}
    )
    assert wrong_password.status_code == no_such_user.status_code == 401
    assert wrong_password.json() == no_such_user.json()


def test_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_full_signup_login_me_logout_flow(client):
    _signup(client)
    client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "correct horse battery"},
    )
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200

    me_after_logout = client.get("/api/v1/auth/me")
    assert me_after_logout.status_code == 401


def test_failed_login_throttling_after_max_attempts(client):
    _signup(client)
    settings = get_settings()
    for _ in range(settings.FAILED_LOGIN_MAX_ATTEMPTS):
        r = client.post(
            "/api/v1/auth/login", json={"email": "alice@example.com", "password": "wrong"}
        )
        assert r.status_code == 401

    throttled = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "correct horse battery"},
    )
    assert throttled.status_code == 429
    assert "Retry-After" in throttled.headers


def test_password_reset_flow_end_to_end(client, db_session):
    _signup(client)
    request_resp = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "alice@example.com"}
    )
    assert request_resp.status_code == 200

    # No email provider is configured (flagged gap) — for the test we
    # go through the service layer directly to obtain the raw token,
    # the same way a real email link would deliver it to the user.
    from app.db.models.password_reset_token import PasswordResetToken

    token_row = db_session.query(PasswordResetToken).one()
    # Reconstruct a raw token that hashes to token_row.token_hash isn't
    # possible (that's the point of hashing) — so exercise the service
    # function directly with a freshly generated token for this test.
    from app.core.security import generate_opaque_token, hash_token

    raw_token = generate_opaque_token()
    token_row.token_hash = hash_token(raw_token)
    db_session.commit()

    confirm_resp = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "brand new password"},
    )
    assert confirm_resp.status_code == 200

    old_password_login = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "correct horse battery"},
    )
    assert old_password_login.status_code == 401

    new_password_login = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "brand new password"},
    )
    assert new_password_login.status_code == 200


def test_password_reset_request_is_enumeration_safe(client):
    known = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "nobody@example.com"}
    )
    _signup(client)
    registered = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "alice@example.com"}
    )
    assert known.status_code == registered.status_code == 200
    assert known.json() == registered.json()


def test_invalid_reset_token_is_rejected(client):
    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "not-a-real-token", "new_password": "whatever12345"},
    )
    assert response.status_code == 400


def test_login_always_calls_verify_password_even_for_nonexistent_user(client, monkeypatch):
    """
    Regression test for a timing side-channel found in adversarial
    review: login() originally short-circuited past verify_password()
    entirely when no user row existed, making 'no such user' return
    measurably faster than 'wrong password' despite an identical
    response body. This asserts the code path itself always reaches
    verify_password — a timing measurement would be flaky in CI, but
    this proves the fix structurally.
    """
    import app.auth.service as service_module

    calls = []
    original = service_module.verify_password

    def spy(password, password_hash):
        calls.append(password_hash)
        return original(password, password_hash)

    monkeypatch.setattr(service_module, "verify_password", spy)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "definitely-nobody@example.com", "password": "whatever"},
    )
    assert response.status_code == 401
    assert len(calls) == 1  # verify_password was called exactly once, not skipped
    assert calls[0] == service_module._DUMMY_HASH_FOR_TIMING_EQUALIZATION


def test_account_deletion_invalidates_session(client):
    _signup(client)
    client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "correct horse battery"},
    )
    delete_resp = client.delete("/api/v1/auth/me")
    assert delete_resp.status_code == 200

    me_after_delete = client.get("/api/v1/auth/me")
    assert me_after_delete.status_code == 401

    login_after_delete = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "correct horse battery"},
    )
    assert login_after_delete.status_code == 401


def test_account_deletion_removes_outstanding_password_reset_tokens(client, db_session):
    """
    Audit finding: delete_account previously left password_reset_tokens
    rows untouched. Functionally harmless (confirm_password_reset
    already checks deleted_at), but an unused reset-token row for a
    deleted account has no purpose. Asserts the row is actually gone,
    not just inert.
    """
    from app.db.models.password_reset_token import PasswordResetToken

    _signup(client)
    client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "correct horse battery"},
    )
    client.post("/api/v1/auth/password-reset/request", json={"email": "alice@example.com"})
    assert db_session.query(PasswordResetToken).count() == 1

    client.delete("/api/v1/auth/me")

    assert db_session.query(PasswordResetToken).count() == 0


def test_password_reset_link_points_at_frontend_not_backend(client, monkeypatch):
    """
    Regression test for the reset-link host bug found in audit: the
    link was built from the backend's own request.base_url instead of
    a configured public frontend URL, so a real emailed link would
    404. Asserts the constructed link's origin matches
    settings.FRONTEND_BASE_URL.
    """
    import app.auth.service as service_module

    captured_links = []

    class _CapturingEmailSender:
        def send_password_reset_email(self, to_email, reset_link):
            captured_links.append(reset_link)

    monkeypatch.setattr(service_module, "ConsoleDevEmailSender", _CapturingEmailSender)

    _signup(client)
    response = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "alice@example.com"}
    )
    assert response.status_code == 200

    settings = get_settings()
    assert len(captured_links) == 1
    assert captured_links[0].startswith(settings.FRONTEND_BASE_URL + "/reset-password?token=")


def test_rbac_require_role_enforced_at_api_layer():
    """
    Phases.md Phase 1: 'RBAC roles present in schema and enforced at
    the API layer.' No admin-only endpoint exists yet under
    /api/v1/auth (correctly — none is required by PRD/Architecture for
    Phase 1), so this proves the require_role dependency itself
    actually rejects/accepts by role, using a minimal probe route
    rather than a real product endpoint that doesn't exist yet.
    """
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from app.auth.dependencies import get_current_user, require_role

    class _FakeUser:
        def __init__(self, role: str):
            self.role = role

    probe_app = FastAPI()

    @probe_app.get("/role-gate")
    def role_gate(user=Depends(require_role("admin"))):
        return {"ok": True, "role": user.role}

    with TestClient(probe_app) as probe_client:
        probe_app.dependency_overrides[get_current_user] = lambda: _FakeUser("user")
        rejected = probe_client.get("/role-gate")
        assert rejected.status_code == 403

        probe_app.dependency_overrides[get_current_user] = lambda: _FakeUser("admin")
        allowed = probe_client.get("/role-gate")
        assert allowed.status_code == 200
        assert allowed.json()["role"] == "admin"
