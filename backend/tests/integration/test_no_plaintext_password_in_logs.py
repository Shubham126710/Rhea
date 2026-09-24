"""
Phases.md Phase 1 exit gate: "no plaintext password ever appears in
logs ... covered by a test that scans log output in CI."
"""
import logging


def test_password_never_appears_in_logs_during_signup_and_login(client, caplog):
    secret_password = "this-exact-string-must-never-be-logged-9f3a"

    with caplog.at_level(logging.DEBUG):
        client.post(
            "/api/v1/auth/signup",
            json={
                "email": "logcheck@example.com",
                "display_name": "Log Check",
                "password": secret_password,
            },
        )
        client.post(
            "/api/v1/auth/login",
            json={"email": "logcheck@example.com", "password": secret_password},
        )
        client.post(
            "/api/v1/auth/login",
            json={"email": "logcheck@example.com", "password": "wrong-" + secret_password},
        )

    full_log_text = caplog.text
    assert secret_password not in full_log_text
    assert ("wrong-" + secret_password) not in full_log_text
