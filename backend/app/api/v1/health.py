"""
Health endpoint — this is the Phase 0 exit-gate round-trip
(Master Build §25 Phase 0 hard exit gate): frontend -> backend -> DB
-> response.

Deliberately the only endpoint in Phase 0. It is real (it genuinely
queries the database), not a placeholder returning a hardcoded 200
(Rules.md §1 Rule 2).
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
