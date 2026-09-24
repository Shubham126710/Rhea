def _signup_login(client, email, password="correct horse battery"):
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "U", "password": password},
    )
    client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_regular_user_gets_403_on_evaluation_summary(client, db_session):
    _signup_login(client, "regularuser@example.com")
    resp = client.get("/api/v1/research/evaluation-summary")
    assert resp.status_code == 403


def test_admin_sees_honest_unavailable_status_not_fabricated_metrics(
    client, db_session, monkeypatch
):
    from app.core.config import get_settings

    get_settings.cache_clear()
    _signup_login(client, "adminuser@example.com")

    from app.db.models.user import User

    user = db_session.query(User).filter(User.email == "adminuser@example.com").first()
    user.role = "admin"
    db_session.commit()

    resp = client.get("/api/v1/research/evaluation-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "no_evaluation_available"
    assert body["metrics"] is None
    get_settings.cache_clear()
