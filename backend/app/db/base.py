"""
Declarative base for all ORM models.

Every model in app/db/models/ imports Base from here, and
alembic/env.py imports Base.metadata from here for autogenerate
support. Kept as its own module (not inline in session.py) so
alembic can import model metadata without also importing the live
engine/session machinery.
"""
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # Every 0001_base_schema.py timestamp column was created as
    # TIMESTAMP(timezone=True) (Architecture.md §4 columns are all
    # TIMESTAMPTZ). Without this, SQLAlchemy's default type inference
    # for a bare `Mapped[datetime]` annotation maps to a naive
    # DateTime(timezone=False) and silently strips tzinfo on every
    # read — a real bug found while implementing Phase 1's password-
    # reset expiry check, not something that showed up in Phase 0
    # (health check never compared datetimes). Fixed once, here, for
    # every model rather than patched per-column.
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }
