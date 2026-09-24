"""
rate_limit_events table — Architecture.md §4.

Optional PostgreSQL backstop; Redis (Architecture.md §6.6) is the
primary rate-limiting mechanism, wired in Phase 5/6. This table exists
now only because it's part of the binding Phase 0 base schema.
"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RateLimitEvent(Base):
    __tablename__ = "rate_limit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    window_start: Mapped[datetime] = mapped_column(nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
