"""/api/v1/analyses/* — Phase 5 (Architecture.md §5)."""
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.analysis_orchestration import service
from app.analysis_orchestration.exceptions import (
    AnalysisNotCancellable,
    AnalysisNotFound,
    ExplanationNotRetryable,
)
from app.analysis_orchestration.jobs import enqueue_analysis, enqueue_explanation
from app.analysis_orchestration.schemas import (
    AnalysisResultResponse,
    AnalysisStatusResponse,
    GraphSubsetResponse,
    MessageResponse,
    SubmitAnalysisRequest,
    SubmitAnalysisResponse,
)
from app.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.core.rate_limit import RateLimitExceeded, check_and_increment
from app.core.redis_client import get_redis
from app.db.models.user import User
from app.db.session import get_db
from app.shared_preprocessing.exceptions import (
    ExtractionFailed,
    FileTooLarge,
    MalformedFile,
    SSRFBlocked,
    UnsupportedFileType,
    URLFetchFailed,
)

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _enforce_rate_limit(user: User, settings: Settings) -> None:
    try:
        check_and_increment(
            get_redis(),
            key=f"analyses_per_hour:{user.id}",
            limit=settings.RATE_LIMIT_ANALYSES_PER_HOUR,
            window_seconds=3600,
        )
    except RateLimitExceeded as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc


def _enforce_concurrency_limit(db: Session, user: User, settings: Settings) -> None:
    in_flight = service.count_in_flight_analyses(db, user=user)
    if in_flight >= settings.RATE_LIMIT_CONCURRENT_ANALYSES:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Too many analyses already in progress "
                f"(limit: {settings.RATE_LIMIT_CONCURRENT_ANALYSES})"
            ),
        )


@router.post("", response_model=SubmitAnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_analysis(
    payload: SubmitAnalysisRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> SubmitAnalysisResponse:
    _enforce_rate_limit(user, settings)
    _enforce_concurrency_limit(db, user, settings)

    try:
        if payload.input_type == "text":
            assert payload.text is not None  # guaranteed by SubmitAnalysisRequest's validator
            ref, was_new = service.submit_text(db, settings, user=user, text=payload.text)
        else:
            assert payload.url is not None  # guaranteed by SubmitAnalysisRequest's validator
            ref, was_new = service.submit_url(db, settings, user=user, url=payload.url)
    except (ExtractionFailed, URLFetchFailed, SSRFBlocked) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if was_new:
        enqueue_analysis(str(ref.analysis_id))

    return SubmitAnalysisResponse(
        analysis_reference_id=ref.id, status="pending" if was_new else "complete"
    )


@router.post("/upload", response_model=SubmitAnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_analysis_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> SubmitAnalysisResponse:
    _enforce_rate_limit(user, settings)
    _enforce_concurrency_limit(db, user, settings)

    content_bytes = await file.read()
    try:
        ref, was_new = service.submit_file(
            db,
            settings,
            user=user,
            filename=file.filename or "upload",
            content_bytes=content_bytes,
            content_type=file.content_type,
            title=file.filename,
        )
    except (ExtractionFailed, MalformedFile, UnsupportedFileType, FileTooLarge) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if was_new:
        enqueue_analysis(str(ref.analysis_id))

    return SubmitAnalysisResponse(
        analysis_reference_id=ref.id, status="pending" if was_new else "complete"
    )


@router.get("/{reference_id}/status", response_model=AnalysisStatusResponse)
def get_analysis_status(
    reference_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalysisStatusResponse:
    try:
        status_value, stage = service.get_status(db, user=user, reference_id=reference_id)
    except AnalysisNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Analysis not found") from exc
    return AnalysisStatusResponse(status=status_value, stage=stage)


@router.get("/{reference_id}", response_model=AnalysisResultResponse)
def get_analysis_result(
    reference_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalysisResultResponse:
    try:
        analysis = service.get_result(db, user=user, reference_id=reference_id)
    except AnalysisNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Analysis not found") from exc

    evidence = analysis.evidence or {}
    stored_graph = evidence.get("graph_subset")
    graph_response = None
    if stored_graph is not None:
        graph_response = GraphSubsetResponse(
            node_ids=stored_graph["node_ids"],
            edges=[tuple(e) for e in stored_graph["edges"]],
            node_relevance=stored_graph["node_relevance"],
            root_index=stored_graph["root_index"],
            truncated=stored_graph["truncated"],
        )

    return AnalysisResultResponse(
        analysis_reference_id=reference_id,
        verdict=analysis.verdict,
        raw_score=float(analysis.raw_score) if analysis.raw_score is not None else None,
        confidence_band=analysis.confidence_band,
        is_calibrated_prob=analysis.is_calibrated_prob,
        model_version=analysis.model_version,
        propagation_available=analysis.propagation_available,
        interaction_available=analysis.interaction_available,
        explanation=analysis.explanation,
        explanation_status=(analysis.extra_metadata or {}).get("explanation_status"),
        attribution_note=evidence.get("attribution_note"),
        graph=graph_response,
        visibility=analysis.visibility,
        created_at=analysis.created_at,
    )


@router.delete("/{reference_id}", response_model=MessageResponse)
def cancel_analysis(
    reference_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageResponse:
    try:
        service.cancel_analysis(db, user=user, reference_id=reference_id)
    except AnalysisNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Analysis not found") from exc
    except AnalysisNotCancellable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return MessageResponse(message="Analysis cancelled.")


@router.post("/{reference_id}/explanation/retry", response_model=MessageResponse)
def retry_explanation(
    reference_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageResponse:
    """PRD §5: "LLM failure or timeout degrades to a visible
    'explanation unavailable — retry' state" -- this is the retry
    action that state implies. Reuses the existing
    should_regenerate_explanation policy and enqueue_explanation job
    (Phase 6) unchanged; only re-enqueues, never re-runs the
    prediction itself, so verdict/raw_score/model_version are
    untouched by a retry."""
    try:
        analysis = service.mark_explanation_retry(db, user=user, reference_id=reference_id)
    except AnalysisNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Analysis not found") from exc
    except ExplanationNotRetryable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    enqueue_explanation(str(analysis.id))
    return MessageResponse(message="Explanation regeneration queued.")
