from app.db.models.analysis import Analysis
from app.db.models.user import User


def _signup_login(client, email, password="correct horse battery"):
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "U", "password": password},
    )
    client.post("/api/v1/auth/login", json={"email": email, "password": password})


def _make_admin(db_session, email):
    user = db_session.query(User).filter(User.email == email).first()
    user.role = "admin"
    db_session.commit()
    return user


def test_regular_user_gets_403_on_model_status(client, db_session):
    _signup_login(client, "regular1@example.com")
    resp = client.get("/api/v1/admin/model-status")
    assert resp.status_code == 403


def test_regular_user_gets_403_on_analysis_metadata(client, db_session):
    _signup_login(client, "regular2@example.com")
    # any UUID-shaped id -- RBAC must reject before the DB lookup happens
    resp = client.get("/api/v1/admin/analyses/00000000-0000-0000-0000-000000000000/metadata")
    assert resp.status_code == 403


def test_admin_sees_model_status_honestly_when_unconfigured(client, db_session, monkeypatch):
    from app.core.config import get_settings

    get_settings.cache_clear()
    _signup_login(client, "admin1@example.com")
    _make_admin(db_session, "admin1@example.com")

    resp = client.get("/api/v1/admin/model-status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "no_model_configured"
    assert body["active_model_version"] is None
    get_settings.cache_clear()


def test_admin_sees_model_status_reflects_configured_version(client, db_session, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("ACTIVE_MODEL_VERSION", "test-model-v1")
    get_settings.cache_clear()
    _signup_login(client, "admin2@example.com")
    _make_admin(db_session, "admin2@example.com")

    resp = client.get("/api/v1/admin/model-status")
    body = resp.json()
    assert body["status"] == "configured"
    assert body["active_model_version"] == "test-model-v1"
    get_settings.cache_clear()


def test_analysis_metadata_matches_architecture_contract_shape(client, db_session, monkeypatch):
    """Architecture.md §5 exact route: GET /admin/analyses/{id}/metadata
    -> dataset_version, model config, eval info."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    _signup_login(client, "admin3@example.com")
    _make_admin(db_session, "admin3@example.com")

    analysis = Analysis(
        content_hash="abc123",
        input_type="text",
        content_reference="some canonical text",
        verdict="fake",
        confidence_band="moderate",
        model_version="test-model-v1",
        dataset_version="upfd-politifact-v1",
        preprocessing_version="1.0.0",
        graph_construction_version="1.0.0",
        calibration_version="uncalibrated-1.0.0",
        evidence={},
        processing_status="complete",
        visibility="private",
        extra_metadata={"stage": "complete"},
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    resp = client.get(f"/api/v1/admin/analyses/{analysis.id}/metadata")
    assert resp.status_code == 200
    body = resp.json()

    assert body["dataset_version"] == "upfd-politifact-v1"
    assert body["model_config"]["model_version"] == "test-model-v1"
    assert body["model_config"]["preprocessing_version"] == "1.0.0"
    assert body["model_config"]["graph_construction_version"] == "1.0.0"
    assert body["model_config"]["calibration_version"] == "uncalibrated-1.0.0"
    # Blocker 2: no real evaluation has ever run -- must be reported
    # honestly, never fabricated.
    assert body["eval_info"]["status"] == "no_evaluation_available"
    assert body["processing_status"] == "complete"

    get_settings.cache_clear()


def test_analysis_metadata_404_for_nonexistent_id(client, db_session):
    _signup_login(client, "admin4@example.com")
    _make_admin(db_session, "admin4@example.com")
    resp = client.get("/api/v1/admin/analyses/00000000-0000-0000-0000-000000000000/metadata")
    assert resp.status_code == 404


def test_analysis_metadata_rejects_malformed_id_before_db_lookup(client, db_session):
    _signup_login(client, "admin5@example.com")
    _make_admin(db_session, "admin5@example.com")
    resp = client.get("/api/v1/admin/analyses/not-a-uuid/metadata")
    assert resp.status_code == 422  # FastAPI's own UUID path-param validation


def test_research_role_also_permitted_on_admin_routes(client, db_session):
    """require_role('admin', 'research') -- confirms 'research' role
    isn't accidentally locked out of admin transparency routes."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    _signup_login(client, "researcher2@example.com")
    user = db_session.query(User).filter(User.email == "researcher2@example.com").first()
    user.role = "research"
    db_session.commit()

    resp = client.get("/api/v1/admin/model-status")
    assert resp.status_code == 200
    get_settings.cache_clear()
