"""
Phase 5 Analysis Orchestration tests — Phases.md's own exit gate,
verbatim: "submitting the same article twice (once as pasted text,
once by URL) produces one analyses row and two private
analysis_references; submitting it a third time after bumping
preprocessing_version in a test produces a second analyses row."
"""
from app.db.models.analysis import Analysis
from app.db.models.analysis_reference import AnalysisReference


def _signup_and_login(client, email="researcher@example.com"):
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "display_name": "Researcher", "password": "correct horse battery"},
    )
    client.post("/api/v1/auth/login", json={"email": email, "password": "correct horse battery"})


def test_submitting_same_article_as_text_and_url_dedupes(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    monkeypatch.setenv("ACTIVE_MODEL_VERSION", "test-model-v0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    import app.shared_preprocessing.pipeline as pipeline_module

    monkeypatch.setattr(
        pipeline_module,
        "fetch_and_extract",
        lambda url: (url, b"The same article content.", "text/plain"),
    )

    _signup_and_login(client)

    text_resp = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "The same article content."}
    )
    assert text_resp.status_code == 202
    assert text_resp.json()["status"] == "pending"

    url_resp = client.post(
        "/api/v1/analyses", json={"input_type": "url", "url": "https://example.com/article"}
    )
    assert url_resp.status_code == 202
    assert url_resp.json()["status"] == "complete"  # dedup hit, pipeline skipped

    assert db_session.query(Analysis).count() == 1
    assert db_session.query(AnalysisReference).count() == 2

    get_settings.cache_clear()


def test_bumping_preprocessing_version_creates_a_second_analysis_row(
    client, db_session, monkeypatch
):
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    monkeypatch.setenv("ACTIVE_MODEL_VERSION", "test-model-v0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    _signup_and_login(client, email="versiontest@example.com")

    first = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "An article about versioning."}
    )
    assert first.status_code == 202

    monkeypatch.setenv("PREPROCESSING_VERSION", "2.0.0")
    get_settings.cache_clear()

    second = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "An article about versioning."}
    )
    assert second.status_code == 202
    assert db_session.query(Analysis).count() == 2

    get_settings.cache_clear()


def test_submission_without_configured_model_still_creates_pending_row(
    client, db_session, monkeypatch
):
    """No ACTIVE_MODEL_VERSION configured (Blocker 2's honest default)
    -- dedup is skipped entirely (nothing to match against), but
    submission itself still succeeds; the pipeline job is what fails
    honestly, not the submission step."""
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    from app.core.config import get_settings

    get_settings.cache_clear()

    _signup_and_login(client, email="nomodel@example.com")
    resp = client.post(
        "/api/v1/analyses",
        json={"input_type": "text", "text": "An article with no model configured."},
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "pending"
    get_settings.cache_clear()


def test_file_upload_is_never_shared_visibility(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    _signup_and_login(client, email="fileupload@example.com")

    resp = client.post(
        "/api/v1/analyses/upload",
        files={"file": ("article.txt", b"Some uploaded article content here.", "text/plain")},
    )
    assert resp.status_code == 202
    ref_id = resp.json()["analysis_reference_id"]

    result = client.get(f"/api/v1/analyses/{ref_id}")
    assert result.json()["visibility"] == "private"


def test_get_status_and_result_reject_another_users_reference(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    _signup_and_login(client, email="alice3@example.com")
    submit = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "Alice's article."}
    )
    ref_id = submit.json()["analysis_reference_id"]
    client.post("/api/v1/auth/logout")

    _signup_and_login(client, email="bob3@example.com")
    assert client.get(f"/api/v1/analyses/{ref_id}/status").status_code == 404
    assert client.get(f"/api/v1/analyses/{ref_id}").status_code == 404


def test_cancel_rejects_already_complete_analysis(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    monkeypatch.setenv("ACTIVE_MODEL_VERSION", "test-model-v0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    _signup_and_login(client, email="carol2@example.com")
    submit = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "Carol's article."}
    )
    ref_id = submit.json()["analysis_reference_id"]

    # Directly mark the underlying analysis complete -- the submit
    # response's own "complete" status (on a dedup hit) reflects "no
    # pipeline work needed," not the analyses.processing_status
    # column, which the pipeline itself is mocked out here and never
    # actually sets.
    analysis = db_session.query(Analysis).join(AnalysisReference).filter(
        AnalysisReference.id == ref_id
    ).first()
    analysis.processing_status = "complete"
    db_session.commit()

    cancel_resp = client.delete(f"/api/v1/analyses/{ref_id}")
    assert cancel_resp.status_code == 409
    get_settings.cache_clear()


def test_result_response_exposes_graph_and_attribution_when_present(
    client, db_session, monkeypatch
):
    """Graph/evidence API contract fix: a completed analysis with a
    persisted graph_subset must surface it via the real API response,
    not just internally in the DB."""
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    monkeypatch.setenv("ACTIVE_MODEL_VERSION", "test-model-v0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    _signup_and_login(client, email="graphcheck@example.com")
    submit = client.post(
        "/api/v1/analyses",
        json={"input_type": "text", "text": "An article to check graph exposure."},
    )
    ref_id = submit.json()["analysis_reference_id"]

    analysis = db_session.query(Analysis).join(AnalysisReference).filter(
        AnalysisReference.id == ref_id
    ).first()
    analysis.processing_status = "complete"
    analysis.verdict = "real"
    analysis.confidence_band = "low"
    analysis.evidence = {
        "attribution_note": "no attention scores for this architecture",
        "graph_subset": {
            "node_ids": [0, 1, 2],
            "edges": [[0, 1, 0], [0, 2, 1]],
            "node_relevance": {"0": 1.0, "1": 0.5, "2": 0.3},
            "root_index": 0,
            "truncated": False,
        },
    }
    db_session.commit()

    result = client.get(f"/api/v1/analyses/{ref_id}")
    assert result.status_code == 200
    body = result.json()
    assert body["attribution_note"] == "no attention scores for this architecture"
    assert body["graph"]["node_ids"] == [0, 1, 2]
    assert body["graph"]["edges"] == [[0, 1, 0], [0, 2, 1]]
    assert body["graph"]["root_index"] == 0
    assert body["graph"]["truncated"] is False
    # Rules.md §2: no layout coordinates anywhere in the response
    assert "x" not in body["graph"]
    assert "y" not in body["graph"]
    assert "positions" not in body["graph"]

    get_settings.cache_clear()


def test_result_response_graph_is_none_when_not_yet_computed(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    monkeypatch.setenv("ACTIVE_MODEL_VERSION", "test-model-v0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    _signup_and_login(client, email="nograph@example.com")
    submit = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "An article without a graph yet."}
    )
    ref_id = submit.json()["analysis_reference_id"]

    result = client.get(f"/api/v1/analyses/{ref_id}")
    assert result.json()["graph"] is None
    assert result.json()["attribution_note"] is None

    get_settings.cache_clear()


# --- Phase 9: concurrency limits (PRD §5) ---


def test_submission_rejected_once_concurrent_limit_reached(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    monkeypatch.setenv("ACTIVE_MODEL_VERSION", "test-model-v0")
    monkeypatch.setenv("RATE_LIMIT_CONCURRENT_ANALYSES", "2")
    from app.core.config import get_settings

    get_settings.cache_clear()

    _signup_and_login(client, email="concurrency@example.com")

    for i in range(2):
        resp = client.post(
            "/api/v1/analyses", json={"input_type": "text", "text": f"Article number {i}."}
        )
        assert resp.status_code == 202

    third = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "Article number 2."}
    )
    assert third.status_code == 429
    assert db_session.query(Analysis).count() == 2  # third was never created

    get_settings.cache_clear()


def test_completed_analyses_do_not_count_toward_concurrent_limit(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    monkeypatch.setenv("ACTIVE_MODEL_VERSION", "test-model-v0")
    monkeypatch.setenv("RATE_LIMIT_CONCURRENT_ANALYSES", "1")
    from app.core.config import get_settings

    get_settings.cache_clear()

    _signup_and_login(client, email="concurrency-complete@example.com")

    first = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "First article."}
    )
    assert first.status_code == 202
    ref_id = first.json()["analysis_reference_id"]

    analysis = (
        db_session.query(Analysis)
        .join(AnalysisReference)
        .filter(AnalysisReference.id == ref_id)
        .first()
    )
    analysis.processing_status = "complete"
    db_session.commit()

    second = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "Second article."}
    )
    assert second.status_code == 202  # the completed one freed the slot

    get_settings.cache_clear()


# --- Phase 9: explanation retry (PRD §5's "explanation unavailable — retry" state) ---


def _complete_analysis_with_explanation_status(db_session, client, ref_id, status_value):
    analysis = (
        db_session.query(Analysis)
        .join(AnalysisReference)
        .filter(AnalysisReference.id == ref_id)
        .first()
    )
    analysis.processing_status = "complete"
    analysis.verdict = "real"
    analysis.confidence_band = "low"
    analysis.extra_metadata = {
        **(analysis.extra_metadata or {}),
        "explanation_status": status_value,
    }
    db_session.commit()
    return analysis


def test_result_response_exposes_explanation_status(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    monkeypatch.setenv("ACTIVE_MODEL_VERSION", "test-model-v0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    _signup_and_login(client, email="explanation-status@example.com")
    submit = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "An article for status check."}
    )
    ref_id = submit.json()["analysis_reference_id"]
    _complete_analysis_with_explanation_status(db_session, client, ref_id, "unavailable")

    result = client.get(f"/api/v1/analyses/{ref_id}")
    assert result.json()["explanation_status"] == "unavailable"

    get_settings.cache_clear()


def test_retry_explanation_requires_ownership(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    monkeypatch.setattr("app.api.v1.analyses.enqueue_explanation", lambda analysis_id: None)
    monkeypatch.setenv("ACTIVE_MODEL_VERSION", "test-model-v0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    _signup_and_login(client, email="retry-owner@example.com")
    submit = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "Owner's article."}
    )
    ref_id = submit.json()["analysis_reference_id"]
    _complete_analysis_with_explanation_status(db_session, client, ref_id, "unavailable")

    _signup_and_login(client, email="retry-other@example.com")
    resp = client.post(f"/api/v1/analyses/{ref_id}/explanation/retry")
    assert resp.status_code == 404  # same not-found-for-non-owner pattern as get/cancel

    get_settings.cache_clear()


def test_retry_explanation_rejected_when_not_in_unavailable_state(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    monkeypatch.setattr("app.api.v1.analyses.enqueue_explanation", lambda analysis_id: None)
    monkeypatch.setenv("ACTIVE_MODEL_VERSION", "test-model-v0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    _signup_and_login(client, email="retry-not-eligible@example.com")
    submit = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "Still processing article."}
    )
    ref_id = submit.json()["analysis_reference_id"]  # left pending -- never completed

    resp = client.post(f"/api/v1/analyses/{ref_id}/explanation/retry")
    assert resp.status_code == 409

    get_settings.cache_clear()


def test_retry_explanation_succeeds_and_enqueues_regeneration(client, db_session, monkeypatch):
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    enqueued: list[str] = []
    monkeypatch.setattr(
        "app.api.v1.analyses.enqueue_explanation", lambda analysis_id: enqueued.append(analysis_id)
    )
    monkeypatch.setenv("ACTIVE_MODEL_VERSION", "test-model-v0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    _signup_and_login(client, email="retry-success@example.com")
    submit = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "Retryable article."}
    )
    ref_id = submit.json()["analysis_reference_id"]
    analysis = _complete_analysis_with_explanation_status(db_session, client, ref_id, "unavailable")

    resp = client.post(f"/api/v1/analyses/{ref_id}/explanation/retry")
    assert resp.status_code == 200
    assert enqueued == [str(analysis.id)]

    # explanation_status flips to "pending" immediately, visible before
    # the (mocked-out) worker ever runs -- proves the retry is real
    # state, not just an enqueue side effect invisible to the API.
    result = client.get(f"/api/v1/analyses/{ref_id}")
    assert result.json()["explanation_status"] == "pending"

    get_settings.cache_clear()


# --- Phase 9: LLM token budget gating (PRD §5's "token budgets for LLM calls") ---


def test_explanation_stage_degrades_honestly_when_daily_token_budget_exhausted(
    db_session, monkeypatch
):
    """Calls pipeline._run_explanation directly (as the RQ worker
    would) with the daily budget pre-exhausted -- proves the pipeline
    refuses the LLM call and degrades to the existing "explanation
    unavailable" state, the same honest path a genuine provider
    failure already takes, rather than silently skipping the budget
    check."""
    import app.analysis_orchestration.pipeline as pipeline_module
    from app.core.config import get_settings
    from app.core.rate_limit import check_and_increment_weighted
    from app.core.redis_client import get_redis

    monkeypatch.setenv("LLM_RATE_LIMIT_TOKENS_PER_DAY", "100")
    get_settings.cache_clear()

    redis_conn = get_redis()
    redis_conn.delete(pipeline_module._LLM_TOKEN_BUDGET_KEY)
    # Pre-spend the entire daily budget in one weighted entry.
    check_and_increment_weighted(
        redis_conn,
        key=pipeline_module._LLM_TOKEN_BUDGET_KEY,
        weight=100,
        limit=10_000_000,  # deliberately high so THIS call itself succeeds
        window_seconds=pipeline_module._LLM_TOKEN_BUDGET_WINDOW_SECONDS,
    )

    analysis = Analysis(
        content_hash="budget-test-hash",
        input_type="text",
        content_reference="budget-test-hash",
        model_version="test-model-v0",
        preprocessing_version="1.0.0",
        graph_construction_version="1.0.0",
        calibration_version="uncalibrated-1.0.0",
        processing_status="complete",
        verdict="real",
        confidence_band="low",
        evidence={},
    )
    db_session.add(analysis)
    db_session.commit()

    pipeline_module._run_explanation(db_session, str(analysis.id))

    db_session.refresh(analysis)
    assert analysis.explanation is None
    assert analysis.extra_metadata["explanation_status"] == "unavailable"
    assert "budget" in analysis.extra_metadata["explanation_error"].lower()

    redis_conn.delete(pipeline_module._LLM_TOKEN_BUDGET_KEY)
    get_settings.cache_clear()


def test_shared_analysis_is_readable_by_a_different_user_via_their_own_search_result(
    db_session, client
):
    """Regression test for a real bug found by inspection: search()
    correctly surfaces other users' visibility='shared' analyses, but
    was returning the *original submitter's* analysis_reference_id for
    those rows -- GET /api/v1/analyses/{id}'s strict ownership check
    then 404'd for every user except the original submitter, silently
    breaking the "shared" feature end-to-end. Fixed in
    service.py::_get_reference_and_analysis_for_read (status/result
    only -- cancellation must still be owner-only regardless of
    visibility, asserted below too)."""
    import uuid

    from app.db.models.analysis import Analysis
    from app.db.models.analysis_reference import AnalysisReference
    from app.db.models.user import User

    owner = User(email="owner@example.com", display_name="Owner", password_hash="x")
    db_session.add(owner)
    db_session.commit()

    shared_analysis = Analysis(
        id=uuid.uuid4(),
        content_hash="hash-shared-1",
        input_type="text",
        content_reference="s3://irrelevant/shared",
        model_version="test-model-v0",
        preprocessing_version="1.0.0",
        graph_construction_version="1.0.0",
        calibration_version="uncalibrated-1.0.0",
        processing_status="complete",
        verdict="real",
        confidence_band="high",
        visibility="shared",
        evidence={},
    )
    private_analysis = Analysis(
        id=uuid.uuid4(),
        content_hash="hash-private-1",
        input_type="text",
        content_reference="s3://irrelevant/private",
        model_version="test-model-v0",
        preprocessing_version="1.0.0",
        graph_construction_version="1.0.0",
        calibration_version="uncalibrated-1.0.0",
        processing_status="complete",
        verdict="fake",
        confidence_band="high",
        visibility="private",
        evidence={},
    )
    db_session.add_all([shared_analysis, private_analysis])
    db_session.commit()

    owners_shared_ref = AnalysisReference(id=uuid.uuid4(), user_id=owner.id, analysis_id=shared_analysis.id)
    owners_private_ref = AnalysisReference(id=uuid.uuid4(), user_id=owner.id, analysis_id=private_analysis.id)
    db_session.add_all([owners_shared_ref, owners_private_ref])
    db_session.commit()

    _signup_and_login(client, email="other-user@example.com")

    # The shared analysis, via the OWNER's reference id -- must be readable.
    shared_resp = client.get(f"/api/v1/analyses/{owners_shared_ref.id}")
    assert shared_resp.status_code == 200
    assert shared_resp.json()["verdict"] == "real"
    assert shared_resp.json()["analysis_reference_id"] == str(owners_shared_ref.id)

    status_resp = client.get(f"/api/v1/analyses/{owners_shared_ref.id}/status")
    assert status_resp.status_code == 200

    # The PRIVATE analysis, via the owner's reference id -- must still 404.
    private_resp = client.get(f"/api/v1/analyses/{owners_private_ref.id}")
    assert private_resp.status_code == 404

    # Cancellation must remain owner-only regardless of visibility --
    # a different user must never be able to cancel someone else's
    # analysis just because it happens to be shared.
    cancel_resp = client.delete(f"/api/v1/analyses/{owners_shared_ref.id}")
    assert cancel_resp.status_code == 404


def test_submit_routes_dispatch_through_orchestration_not_the_api_layer(
    client, db_session, monkeypatch
):
    """Regression test for the orchestration-boundary fix: the API
    layer (app/api/v1/analyses.py) no longer imports or calls
    Shared Preprocessing directly -- it calls
    service.submit_text/submit_url/submit_file, which now own the
    preprocess_*() dispatch (Architecture.md's responsibility table:
    Analysis Orchestration "accept submission -> dispatch to
    preprocessing"; this module's own docstring: "Only this module
    calls Shared Preprocessing ... directly"). This test proves text,
    URL, and file submission all still work end-to-end through the
    new call path -- same behavior, different module boundary.

    Also regression-covers the filename bug found while making this
    move: file uploads must use the raw filename as the stored
    `title`, not the "upload" fallback that exists only for the
    internal preprocessing call (which needs a non-empty filename to
    detect a file type from).
    """
    monkeypatch.setattr("app.api.v1.analyses.enqueue_analysis", lambda analysis_id: None)
    monkeypatch.setenv("ACTIVE_MODEL_VERSION", "test-model-v0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    import app.shared_preprocessing.pipeline as pipeline_module

    monkeypatch.setattr(
        pipeline_module,
        "fetch_and_extract",
        lambda url: (url, b"An article fetched from a URL.", "text/plain"),
    )

    _signup_and_login(client, email="boundary-test@example.com")

    # Text submission still works and still creates a pending analysis.
    text_resp = client.post(
        "/api/v1/analyses", json={"input_type": "text", "text": "An article submitted as raw text."}
    )
    assert text_resp.status_code == 202
    assert text_resp.json()["status"] == "pending"

    # URL submission still works (goes through the same dispatch path).
    url_resp = client.post(
        "/api/v1/analyses", json={"input_type": "url", "url": "https://example.com/a-different-article"}
    )
    assert url_resp.status_code == 202
    assert url_resp.json()["status"] == "pending"

    # File submission still works, and the stored title is the exact
    # original filename, not the "upload" preprocessing fallback.
    file_resp = client.post(
        "/api/v1/analyses/upload",
        files={"file": ("my-report.txt", b"Report content for the analysis.", "text/plain")},
    )
    assert file_resp.status_code == 202
    file_ref_id = file_resp.json()["analysis_reference_id"]

    from app.db.models.analysis import Analysis
    from app.db.models.analysis_reference import AnalysisReference

    file_ref = db_session.get(AnalysisReference, file_ref_id)
    file_analysis = db_session.get(Analysis, file_ref.analysis_id)
    assert file_analysis.title == "my-report.txt"  # not "upload"

    get_settings.cache_clear()
