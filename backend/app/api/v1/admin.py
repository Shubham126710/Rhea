"""/api/v1/admin/* — Phase 8, Architecture.md §5.

    GET /api/v1/admin/analyses/{id}/metadata — RBAC-gated: dataset_version,
    model config, eval info (exact wording, Architecture.md §5)

RBAC-gated via the existing require_role dependency (Phase 1)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.core.config import Settings, get_settings
from app.db.models.analysis import Analysis
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/model-status")
def get_model_status(
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_role("admin", "research")),
) -> dict:
    """Deeper model/version transparency reserved for admin/research
    (PRD §4.2/Batch C) — regular users only ever see the fields
    already exposed on AnalysisResultResponse."""
    return {
        "active_model_version": settings.ACTIVE_MODEL_VERSION or None,
        "model_artifact_dir": settings.MODEL_ARTIFACT_DIR or None,
        "graph_construction_version": settings.GRAPH_CONSTRUCTION_VERSION,
        "calibration_version": settings.CALIBRATION_VERSION,
        "preprocessing_version": settings.PREPROCESSING_VERSION,
        "status": "configured" if settings.ACTIVE_MODEL_VERSION else "no_model_configured",
    }


@router.get("/analyses/{analysis_id}/metadata")
def get_analysis_metadata(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin", "research")),
) -> dict:
    """Exact route/response contract from Architecture.md §5: dataset_version,
    model config, eval info — not raw research artifacts (that
    restriction belongs to /research/evaluation-summary, this route's
    job is per-analysis admin transparency)."""
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return {
        "id": str(analysis.id),
        "content_hash": analysis.content_hash,
        "dataset_version": analysis.dataset_version,
        "model_config": {
            "model_version": analysis.model_version,
            "preprocessing_version": analysis.preprocessing_version,
            "graph_construction_version": analysis.graph_construction_version,
            "calibration_version": analysis.calibration_version,
        },
        "eval_info": {
            # No real evaluation has been run for any model_version yet
            # (Blocker 2) -- reporting that honestly rather than
            # fabricating metrics, same pattern as
            # /research/evaluation-summary.
            "status": "no_evaluation_available",
        },
        "processing_status": analysis.processing_status,
        "extra_metadata": analysis.extra_metadata,
    }
