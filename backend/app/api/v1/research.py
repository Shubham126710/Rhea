"""/api/v1/research/* — Architecture.md §5, Phases.md Phase 8.
RBAC-gated, reuses the existing require_role dependency (Phase 1)."""
from fastapi import APIRouter, Depends

from app.auth.dependencies import require_role
from app.core.config import Settings, get_settings
from app.db.models.user import User

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/evaluation-summary")
def get_evaluation_summary(
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_role("admin", "research")),
) -> dict:
    """Aggregate metrics only, never raw research artifacts
    (Architecture.md §5's own restriction on this route). No real
    trained model/evaluation exists yet (Blocker 2) — this reports
    that plainly rather than fabricating metrics, following the same
    honesty pattern as Phase 5/6's other unresolved-dependency paths
    (graph_features.py, NoAPIKeyConfiguredProvider)."""
    if not settings.ACTIVE_MODEL_VERSION:
        return {
            "status": "no_evaluation_available",
            "reason": "No trained model artifact is configured (research blocker, unresolved).",
            "model_version": None,
            "metrics": None,
        }

    return {
        "status": "no_evaluation_available",
        "reason": (
            f"Model version {settings.ACTIVE_MODEL_VERSION!r} is configured, but no "
            f"evaluation run has been recorded for it yet."
        ),
        "model_version": settings.ACTIVE_MODEL_VERSION,
        "metrics": None,
    }
