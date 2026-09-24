"""
FastAPI-facing auth dependencies.

This is the one place that's allowed to know both about FastAPI
(Request/HTTPException) and about app.auth.service — kept separate
from service.py itself so service.py stays framework-agnostic
(Rules.md §3.1).
"""
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import service
from app.core.config import Settings, get_settings
from app.db.models.user import User
from app.db.session import get_db


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if raw_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = service.get_user_by_session_token(db, raw_token)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_role(*allowed_roles: str) -> Callable[[User], User]:
    """RBAC dependency factory (Phases.md Phase 1: 'RBAC roles present
    in schema and enforced at the API layer'). Only user/admin are
    meaningfully exercised in Phase 1; `research` exists in the schema
    for later phases (PRD Batch C)."""

    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _check
