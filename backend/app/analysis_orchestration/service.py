"""
Analysis Orchestration service — Phases.md Phase 5, Architecture.md
§5/§6.2/§6.3. Only this module calls Shared Preprocessing, ML
Inference, Graph Processor, and (Phase 6) the LLM Adapter directly
(Rules.md §2 — module isolation).
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analysis_orchestration.dedup import find_existing_analysis
from app.analysis_orchestration.exceptions import (
    AnalysisNotCancellable,
    AnalysisNotFound,
    ExplanationNotRetryable,
)
from app.analysis_orchestration.visibility import decide_visibility
from app.core.config import Settings
from app.db.models.analysis import Analysis
from app.db.models.analysis_reference import AnalysisReference
from app.db.models.user import User
from app.shared_preprocessing.pipeline import (
    preprocess_file,
    preprocess_pasted_text,
    preprocess_url,
)


def create_reference(db: Session, *, user: User, analysis: Analysis) -> AnalysisReference:
    """Always private to the user, regardless of the analysis's own
    visibility (Architecture.md §4)."""
    ref = AnalysisReference(user_id=user.id, analysis_id=analysis.id)
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


def submit_analysis(
    db: Session,
    settings: Settings,
    *,
    user: User,
    content_hash: str,
    input_type: str,
    source_url: str | None,
    content_reference: str,
    title: str | None,
) -> tuple[AnalysisReference, bool]:
    """Returns (reference, was_new). Dedup hit: only a new reference
    is created, pipeline is skipped entirely. No match: a new pending
    analyses row + reference are created; caller enqueues the job."""
    model_version = settings.ACTIVE_MODEL_VERSION
    preprocessing_version = settings.PREPROCESSING_VERSION
    graph_construction_version = settings.GRAPH_CONSTRUCTION_VERSION
    calibration_version = settings.CALIBRATION_VERSION

    existing = None
    if model_version:
        existing = find_existing_analysis(
            db,
            content_hash=content_hash,
            model_version=model_version,
            preprocessing_version=preprocessing_version,
            graph_construction_version=graph_construction_version,
            calibration_version=calibration_version,
        )

    if existing is not None:
        ref = create_reference(db, user=user, analysis=existing)
        return ref, False

    visibility = decide_visibility(
        input_type=input_type,
        source_url=source_url,
        canonical_text=content_reference,
        settings=settings,
    )

    analysis = Analysis(
        content_hash=content_hash,
        input_type=input_type,
        source_url=source_url,
        title=title,
        content_reference=content_reference,
        verdict="",
        confidence_band="",
        model_version=model_version,
        preprocessing_version=preprocessing_version,
        graph_construction_version=graph_construction_version,
        calibration_version=calibration_version,
        evidence={},
        processing_status="pending",
        visibility=visibility,
        extra_metadata={},
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    ref = create_reference(db, user=user, analysis=analysis)
    return ref, True


def submit_text(
    db: Session, settings: Settings, *, user: User, text: str, title: str | None = None
) -> tuple[AnalysisReference, bool]:
    """Dispatch to Shared Preprocessing, then submit_analysis.

    BOUNDARY FIX: this call (and submit_url/submit_file below) used to
    happen in app/api/v1/analyses.py itself -- the API route called
    preprocess_pasted_text/preprocess_url/preprocess_file directly and
    handed the already-preprocessed result to submit_analysis. That
    contradicts both Architecture.md's own responsibility table
    ("Analysis Orchestration ... accept submission -> dispatch to
    preprocessing") and this module's own docstring ("Only this module
    calls Shared Preprocessing ... directly"). Moved here verbatim --
    same functions, same arguments, same exceptions propagating
    unchanged to the API layer's existing try/except -- so this is a
    responsibility-boundary fix, not a behavior change.
    """
    preprocessed = preprocess_pasted_text(text)
    return submit_analysis(
        db,
        settings,
        user=user,
        content_hash=preprocessed.content_hash,
        input_type="text",
        source_url=None,
        content_reference=preprocessed.canonical_text,
        title=title,
    )


def submit_url(
    db: Session, settings: Settings, *, user: User, url: str, title: str | None = None
) -> tuple[AnalysisReference, bool]:
    preprocessed = preprocess_url(url)
    return submit_analysis(
        db,
        settings,
        user=user,
        content_hash=preprocessed.content_hash,
        input_type="url",
        source_url=url,
        content_reference=preprocessed.canonical_text,
        title=title,
    )


def submit_file(
    db: Session,
    settings: Settings,
    *,
    user: User,
    filename: str,
    content_bytes: bytes,
    content_type: str | None,
    title: str | None,
) -> tuple[AnalysisReference, bool]:
    preprocessed = preprocess_file(filename, content_bytes, content_type)
    return submit_analysis(
        db,
        settings,
        user=user,
        content_hash=preprocessed.content_hash,
        input_type="file",
        source_url=None,
        content_reference=preprocessed.canonical_text,
        title=title,
    )


def get_reference_for_user(db: Session, *, user: User, reference_id: UUID) -> AnalysisReference:
    ref = db.execute(
        select(AnalysisReference).where(
            AnalysisReference.id == reference_id, AnalysisReference.user_id == user.id
        )
    ).scalar_one_or_none()
    if ref is None:
        raise AnalysisNotFound()
    return ref


def _get_reference_and_analysis_for_read(
    db: Session, *, user: User, reference_id: UUID
) -> tuple[AnalysisReference, Analysis]:
    """Read access only (status/result) -- the caller's own reference,
    OR any reference at all when the underlying analysis is genuinely
    visibility='shared'.

    BUG FIX: `search()` below correctly surfaces other users'
    visibility='shared' analyses, but the analysis_reference_id it
    returns for those rows is the *original submitter's*
    AnalysisReference row (there's only ever one reference per
    analysis unless a user explicitly reruns it themselves) --
    get_reference_for_user's strict `user_id == user.id` check would
    404 every single one of those for anyone but the original
    submitter, silently breaking the "shared" feature end-to-end for
    every other user. Architecture.md's own definition of
    visibility='shared' is "anyone can view it", so a reference to a
    shared analysis is a valid read path regardless of who owns that
    specific reference row.

    Deliberately NOT used by cancel_analysis: cancelling someone
    else's analysis must never be allowed, visibility notwithstanding
    -- that keeps using get_reference_for_user directly, unchanged.
    """
    ref = db.execute(
        select(AnalysisReference).where(AnalysisReference.id == reference_id)
    ).scalar_one_or_none()
    if ref is None:
        raise AnalysisNotFound()
    analysis = db.get(Analysis, ref.analysis_id)
    if analysis is None:
        raise AnalysisNotFound()
    if ref.user_id != user.id and analysis.visibility != "shared":
        # Do not distinguish this from "not found" -- confirming that
        # a private analysis_reference_id merely *exists* for someone
        # else is itself a private-metadata leak.
        raise AnalysisNotFound()
    return ref, analysis


def get_status(db: Session, *, user: User, reference_id: UUID) -> tuple[str, str | None]:
    _ref, analysis = _get_reference_and_analysis_for_read(db, user=user, reference_id=reference_id)
    stage = analysis.extra_metadata.get("stage") if analysis.extra_metadata else None
    return analysis.processing_status, stage


def get_result(db: Session, *, user: User, reference_id: UUID) -> Analysis:
    _ref, analysis = _get_reference_and_analysis_for_read(db, user=user, reference_id=reference_id)
    return analysis


def cancel_analysis(db: Session, *, user: User, reference_id: UUID) -> None:
    ref = get_reference_for_user(db, user=user, reference_id=reference_id)
    analysis = db.get(Analysis, ref.analysis_id)
    if analysis is None:
        raise AnalysisNotFound()
    if analysis.processing_status not in ("pending", "processing"):
        raise AnalysisNotCancellable(analysis.processing_status)
    analysis.processing_status = "failed"
    analysis.extra_metadata = {**(analysis.extra_metadata or {}), "cancelled": True}
    db.commit()


def mark_explanation_retry(db: Session, *, user: User, reference_id: UUID) -> Analysis:
    """PRD §5: the explicit "explanation unavailable — retry" state's
    retry action. Only eligible once the prediction itself is
    complete and the explanation genuinely failed (extra_metadata's
    explanation_status == "unavailable") -- retrying a still-pending
    prediction or a successful explanation isn't a real "retry",
    it's either premature or a no-op, and both are rejected rather
    than silently accepted. Sets explanation_status back to "pending"
    so the frontend's existing status handling reflects the retry is
    in flight; the caller (api/v1/analyses.py) is responsible for the
    actual enqueue_explanation(...) call, matching how submit_analysis
    never enqueues itself either (Rules.md §3.3-adjacent: queue
    dispatch stays at the API layer, not inside service.py)."""
    ref = get_reference_for_user(db, user=user, reference_id=reference_id)
    analysis = db.get(Analysis, ref.analysis_id)
    if analysis is None:
        raise AnalysisNotFound()
    if analysis.processing_status != "complete":
        raise ExplanationNotRetryable(
            f"Cannot retry explanation for an analysis with status {analysis.processing_status!r}"
        )
    explanation_status = (analysis.extra_metadata or {}).get("explanation_status")
    if explanation_status != "unavailable":
        raise ExplanationNotRetryable(
            f"Explanation is not in a retryable state (current: {explanation_status!r})"
        )
    analysis.extra_metadata = {**(analysis.extra_metadata or {}), "explanation_status": "pending"}
    db.commit()
    return analysis


def count_in_flight_analyses(db: Session, *, user: User) -> int:
    """PRD §5's "concurrency limits" -- how many of this user's own
    analyses are currently pending/processing. Reuses the existing
    AnalysisReference -> Analysis relationship (same join list_history
    already uses) rather than a new Redis primitive: this is a point-
    in-time DB count, not a sliding window, which is what "how many
    are in flight right now" actually needs."""
    return db.execute(
        select(func.count())
        .select_from(AnalysisReference)
        .join(Analysis, AnalysisReference.analysis_id == Analysis.id)
        .where(
            AnalysisReference.user_id == user.id,
            Analysis.processing_status.in_(("pending", "processing")),
        )
    ).scalar_one()


def list_history(
    db: Session, *, user: User, limit: int = 20, offset: int = 0
) -> tuple[list[tuple[AnalysisReference, Analysis]], int]:
    query = (
        select(AnalysisReference, Analysis)
        .join(Analysis, AnalysisReference.analysis_id == Analysis.id)
        .where(AnalysisReference.user_id == user.id)
        .order_by(AnalysisReference.created_at.desc())
    )
    all_rows = [tuple(row) for row in db.execute(query).all()]
    page = all_rows[offset : offset + limit]
    return page, len(all_rows)


def search(
    db: Session, *, user: User, query_text: str, limit: int = 20
) -> list[tuple[AnalysisReference, Analysis]]:
    """Private history + permitted shared analyses only (Architecture
    §4/PRD §4.7) — never every analysis ever submitted."""
    own = (
        select(AnalysisReference, Analysis)
        .join(Analysis, AnalysisReference.analysis_id == Analysis.id)
        .where(AnalysisReference.user_id == user.id, Analysis.title.ilike(f"%{query_text}%"))
    )
    shared = (
        select(AnalysisReference, Analysis)
        .join(Analysis, AnalysisReference.analysis_id == Analysis.id)
        .where(Analysis.visibility == "shared", Analysis.title.ilike(f"%{query_text}%"))
    )
    own_results = [tuple(row) for row in db.execute(own).all()]
    seen_analysis_ids = {a.id for _ref, a in own_results}
    shared_results = [
        tuple(row) for row in db.execute(shared).all() if row[1].id not in seen_analysis_ids
    ]
    return (own_results + shared_results)[:limit]
