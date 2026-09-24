"""
Account-deletion cascade — Architecture.md §6.5. Called from the API
layer alongside auth.service.delete_account, NOT called by auth/
itself (Rules.md §2 module-isolation direction — auth must not reach
into analysis_orchestration).

users.id -> analysis_references.user_id is ON DELETE CASCADE, but
Phase 1 account deletion is a soft delete (users.deleted_at), so that
FK cascade never fires. This function performs the equivalent
cleanup explicitly. analyses.id -> analysis_references.analysis_id is
ON DELETE RESTRICT, so private analyses' references must be deleted
BEFORE the now-orphaned analyses row itself can be deleted.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.analysis import Analysis
from app.db.models.analysis_reference import AnalysisReference


def purge_user_analyses(db: Session, user_id: UUID) -> None:
    references = db.query(AnalysisReference).filter(AnalysisReference.user_id == user_id).all()

    for ref in references:
        analysis = db.get(Analysis, ref.analysis_id)
        db.delete(ref)
        db.flush()  # RESTRICT FK requires the reference gone before the analyses row can go

        if analysis is not None and analysis.visibility == "private":
            # Nothing else can reference a private analysis (by
            # construction — visibility.py never promotes it), so
            # it's now safe to remove.
            other_refs = (
                db.query(AnalysisReference)
                .filter(AnalysisReference.analysis_id == analysis.id)
                .count()
            )
            if other_refs == 0:
                db.delete(analysis)
        # shared analyses: reference removed above, analyses row
        # untouched and never was attributed to this user's identity
        # beyond the now-deleted reference (Architecture §6.5).

    db.commit()
