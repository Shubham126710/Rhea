"""
Analysis Orchestration pipeline — Architecture.md §6.3 staged worker.
Extraction already happened synchronously at submission time (see
api/v1/analyses.py), so this job starts at preparing_features.
"""
from __future__ import annotations

import traceback
from uuid import UUID


def _set_stage(analysis, stage: str) -> None:
    analysis.extra_metadata = {**(analysis.extra_metadata or {}), "stage": stage}


def run_analysis_pipeline(analysis_id: str) -> None:
    """RQ job entry point — opens its own DB session since RQ workers
    run in a separate process from the request."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        _run(db, analysis_id)
    finally:
        db.close()


def _run(db, analysis_id: str) -> None:
    from app.analysis_orchestration.graph_features import (
        FeatureConstructionNotResolved,
        build_live_graph,
    )
    from app.analysis_orchestration.jobs import enqueue_explanation
    from app.core.config import get_settings
    from app.db.models.analysis import Analysis
    from app.ml_inference.model_loader import load_model_artifact_cached

    settings = get_settings()
    analysis = db.get(Analysis, UUID(analysis_id))
    if analysis is None:
        return

    try:
        analysis.processing_status = "processing"
        _set_stage(analysis, "preparing_features")
        db.commit()

        if not settings.ACTIVE_MODEL_VERSION:
            raise RuntimeError(
                "No ACTIVE_MODEL_VERSION configured — no real trained model "
                "artifact exists yet (Blocker 2). Refusing to fabricate a verdict."
            )

        loaded = load_model_artifact_cached(
            checkpoint_dir=settings.MODEL_ARTIFACT_DIR,
            manifest_path=settings.MODEL_MANIFEST_PATH,
            model_version=settings.ACTIVE_MODEL_VERSION,
        )

        _set_stage(analysis, "building_graph")
        db.commit()
        try:
            graph = build_live_graph(
                analysis.content_reference, expected_in_channels=loaded.in_channels
            )
        except FeatureConstructionNotResolved as exc:
            raise RuntimeError(str(exc)) from exc

        _set_stage(analysis, "running_model")
        db.commit()
        from app.ml_inference.inference import run_inference

        result = run_inference(graph, loaded)

        from app.graph_processor.filtering import build_graph_subset

        graph_subset = build_graph_subset(graph, max_nodes=settings.GRAPH_MAX_NODES)

        _set_stage(analysis, "finalizing")
        analysis.verdict = result.verdict
        analysis.raw_score = result.raw_score
        analysis.confidence_band = result.confidence_band
        analysis.is_calibrated_prob = result.is_calibrated_prob
        analysis.propagation_available = result.propagation_available
        analysis.interaction_available = result.interaction_available
        analysis.evidence = {
            "attribution_note": result.attribution.note,
            # Full GraphSubset persisted here (Rules.md §2: still no
            # coordinates, unchanged shape) rather than discarding it
            # down to a bare count -- Phase 7 needs the actual
            # nodes/edges/relevance to render anything, and this is
            # the existing evidence JSONB column already designed to
            # hold exactly this kind of pipeline output, so no new
            # migration or table is needed.
            "graph_subset": {
                "node_ids": graph_subset.node_ids,
                "edges": [list(e) for e in graph_subset.edges],
                "node_relevance": {str(k): v for k, v in graph_subset.node_relevance.items()},
                "root_index": graph_subset.root_index,
                "truncated": graph_subset.truncated,
            },
        }
        analysis.processing_status = "complete"
        _set_stage(analysis, "generating_explanation")
        db.commit()

        enqueue_explanation(str(analysis.id))

    except Exception as exc:  # noqa: BLE001 -- this job's own top-level error boundary
        analysis.processing_status = "failed"
        analysis.extra_metadata = {
            **(analysis.extra_metadata or {}),
            "stage": "failed",
            "error": str(exc),
            "error_type": type(exc).__name__,
        }
        db.commit()
        raise
    finally:
        if analysis.processing_status not in ("complete", "failed"):
            traceback.print_exc()


def run_explanation_stage(analysis_id: str) -> None:
    """Phase 6 stage — separate queue (core/queue.py) so a slow/failed
    LLM call never blocks the already-complete prediction from being
    served (PRD §4.5)."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        _run_explanation(db, analysis_id)
    finally:
        db.close()


def _run_explanation(db, analysis_id: str) -> None:
    from app.db.models.analysis import Analysis
    from app.llm_adapter.adapter import generate_explanation
    from app.llm_adapter.evidence_builder import build_evidence_payload
    from app.llm_adapter.exceptions import ExplanationGenerationFailed
    from app.llm_adapter.reuse import should_regenerate_explanation
    from app.ml_inference.schemas import AttributionData, PredictionResult

    analysis = db.get(Analysis, UUID(analysis_id))
    if analysis is None or analysis.processing_status != "complete":
        return

    if not should_regenerate_explanation(analysis):
        return

    prediction = PredictionResult(
        verdict=analysis.verdict,
        raw_score=float(analysis.raw_score) if analysis.raw_score is not None else 0.0,
        confidence_band=analysis.confidence_band,
        is_calibrated_prob=analysis.is_calibrated_prob,
        attribution=AttributionData(),
        model_version=analysis.model_version,
        propagation_available=analysis.propagation_available,
        interaction_available=analysis.interaction_available,
    )
    stored_graph = (analysis.evidence or {}).get("graph_subset")
    node_count = len(stored_graph["node_ids"]) if stored_graph else None
    evidence = build_evidence_payload(prediction, graph_node_count=node_count)

    try:
        _check_llm_token_budget()
        explanation, tokens_used = generate_explanation(evidence)
        _record_llm_token_usage(tokens_used)
        explanation_dict = explanation.model_dump()
        explanation_dict["_generated_for_model_version"] = analysis.model_version
        analysis.explanation = explanation_dict
        analysis.extra_metadata = {
            **(analysis.extra_metadata or {}),
            "explanation_status": "complete",
            "stage": "complete",
        }
    except ExplanationGenerationFailed as exc:
        analysis.explanation = None
        analysis.extra_metadata = {
            **(analysis.extra_metadata or {}),
            "explanation_status": "unavailable",
            "explanation_error": str(exc),
            "stage": "complete",
        }
    db.commit()


_LLM_TOKEN_BUDGET_KEY = "llm_tokens_per_day"
_LLM_TOKEN_BUDGET_WINDOW_SECONDS = 86400


def _check_llm_token_budget() -> None:
    """PRD §5's "token budgets for LLM calls" -- checked here, not in
    llm_adapter/adapter.py, so adapter.py stays Redis-free and unit-
    testable (Architecture.md §10: Redis is an integration-tier
    concern). Raises ExplanationGenerationFailed -- no new exception
    type -- so the existing except clause immediately below already
    degrades this to the existing "explanation unavailable" state."""
    from app.core.config import get_settings
    from app.core.rate_limit import current_weighted_total
    from app.core.redis_client import get_redis
    from app.llm_adapter.exceptions import ExplanationGenerationFailed

    settings = get_settings()
    already_spent = current_weighted_total(
        get_redis(), key=_LLM_TOKEN_BUDGET_KEY, window_seconds=_LLM_TOKEN_BUDGET_WINDOW_SECONDS
    )
    if already_spent >= settings.LLM_RATE_LIMIT_TOKENS_PER_DAY:
        raise ExplanationGenerationFailed(
            f"Daily LLM token budget ({settings.LLM_RATE_LIMIT_TOKENS_PER_DAY}) already spent"
        )


def _record_llm_token_usage(tokens_used: int) -> None:
    from app.core.config import get_settings
    from app.core.rate_limit import RateLimitExceeded, check_and_increment_weighted
    from app.core.redis_client import get_redis

    settings = get_settings()
    try:
        check_and_increment_weighted(
            get_redis(),
            key=_LLM_TOKEN_BUDGET_KEY,
            weight=tokens_used,
            limit=settings.LLM_RATE_LIMIT_TOKENS_PER_DAY,
            window_seconds=_LLM_TOKEN_BUDGET_WINDOW_SECONDS,
        )
    except RateLimitExceeded:
        # This call already succeeded and is already paid for -- the
        # budget being now exhausted only affects the *next* call,
        # which _check_llm_token_budget() refuses pre-flight.
        pass
