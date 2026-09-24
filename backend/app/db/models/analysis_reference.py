"""
analysis_references table — Architecture.md §4.

The private relationship: user <-> analysis. Always private to the
user regardless of the referenced analysis's visibility. History and
Search (Phase 5/7) query this table joined to `analyses`.

ON DELETE RESTRICT on analysis_id: an `analyses` row must never be
deleted out from under a reference that still points to it — Phase 5's
account-deletion mechanism (Architecture.md §6.5) removes the
analysis_references row first, and only removes the analyses row
itself when it was private and now orphaned.
"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class AnalysisReference(Base):
    __tablename__ = "analysis_references"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
