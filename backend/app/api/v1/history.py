"""/api/v1/history — PRD §4.7."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analysis_orchestration import service
from app.analysis_orchestration.schemas import HistoryItem, HistoryResponse
from app.auth.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryResponse)
def get_history(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HistoryResponse:
    rows, total = service.list_history(db, user=user, limit=limit, offset=offset)
    items = [
        HistoryItem(
            analysis_reference_id=ref.id,
            title=analysis.title,
            verdict=analysis.verdict,
            confidence_band=analysis.confidence_band,
            processing_status=analysis.processing_status,
            created_at=ref.created_at,
        )
        for ref, analysis in rows
    ]
    return HistoryResponse(items=items, total=total)
