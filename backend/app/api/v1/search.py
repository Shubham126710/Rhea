"""/api/v1/search — private history + permitted shared analyses only (PRD §4.7)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analysis_orchestration import service
from app.analysis_orchestration.schemas import HistoryItem, SearchResponse
from app.auth.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search_analyses(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SearchResponse:
    rows = service.search(db, user=user, query_text=q)
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
    return SearchResponse(items=items)
