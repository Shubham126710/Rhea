"""
Aggregates all /api/v1 routes.

Phase 0 registered only health. Phase 1 adds auth. Later phases
register their routers here (analyses, search, history, admin,
research) — Architecture.md §5.
"""
from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.analyses import router as analyses_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.history import router as history_router
from app.api.v1.research import router as research_router
from app.api.v1.search import router as search_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(auth_router)
api_v1_router.include_router(analyses_router)
api_v1_router.include_router(history_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(research_router)
