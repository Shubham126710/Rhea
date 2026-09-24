"""
Phases.md Phase 1 exit gate, verbatim: "full E2E path signup -> login
-> logout -> password reset -> account deletion passes."

Implemented as a backend-driven flow through real HTTP endpoints and
a real database (not mocked) rather than a Playwright browser test —
flagged in the implementation report as a scope decision, since
there's no real frontend UI yet for Playwright to drive. Full browser
E2E (Architecture.md §10 / Rules.md §5) is Phase 7's job, once the
actual UI exists.
"""
from app.db.models.password_reset_token import PasswordResetToken


def test_full_auth_lifecycle_signup_login_logout_reset_delete(client, db_session):
    email = "e2e@example.com"
    original_password = "original password one"
    new_password = "brand new password two"

    # 1. Signup
    signup_resp = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "E2E User", "password": original_password},
    )
    assert signup_resp.status_code == 201

    # 2. Login
    login_resp = client.post(
        "/api/v1/auth/login", json={"email": email, "password": original_password}
    )
    assert login_resp.status_code == 200
    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email

    # 3. Logout
    logout_resp = client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401

    # 4. Password reset (request -> obtain token via the DB, the same
    # way a real email link would deliver it -> confirm -> old
    # password rejected, new password accepted)
    reset_request_resp = client.post(
        "/api/v1/auth/password-reset/request", json={"email": email}
    )
    assert reset_request_resp.status_code == 200

    from app.core.security import generate_opaque_token, hash_token

    raw_reset_token = generate_opaque_token()
    token_row = db_session.query(PasswordResetToken).order_by(
        PasswordResetToken.expires_at.desc()
    ).first()
    token_row.token_hash = hash_token(raw_reset_token)
    db_session.commit()

    confirm_resp = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_reset_token, "new_password": new_password},
    )
    assert confirm_resp.status_code == 200

    assert (
        client.post(
            "/api/v1/auth/login", json={"email": email, "password": original_password}
        ).status_code
        == 401
    )
    relogin_resp = client.post(
        "/api/v1/auth/login", json={"email": email, "password": new_password}
    )
    assert relogin_resp.status_code == 200

    # 5. Account deletion -> session invalidated -> login no longer works
    delete_resp = client.delete("/api/v1/auth/me")
    assert delete_resp.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": email, "password": new_password}
        ).status_code
        == 401
    )
