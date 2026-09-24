"""
analyses table — Architecture.md §4, §6.2.

The reusable computational artifact. `id` is the sole cross-table
identity (Master Build §9, Rules.md §2) — the five-value version
tuple below is a UNIQUE constraint used only for deduplication
lookups in Analysis Orchestration (Phase 5), never stored or treated
as an identity anywhere else.

content_hash canonicalization note (Architecture.md §4/§13, Master
Build §9.3): this column holds the hash of the FULLY EXTRACTED AND
NORMALIZED TEXT produced by Shared Preprocessing (Phase 2) — the same
canonical text fed to the text encoder. input_type is stored for
display/audit only and is deliberately excluded from the uniqueness
identity.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        UniqueConstraint(
            "content_hash",
            "model_version",
            "preprocessing_version",
            "graph_construction_version",
            "calibration_version",
            name="uq_analyses_dedup_tuple",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content_hash: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    input_type: Mapped[str] = mapped_column(Text, nullable=False)  # 'text'|'url'|'file'
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_reference: Mapped[str] = mapped_column(Text, nullable=False)

    verdict: Mapped[str] = mapped_column(Text, nullable=False)  # 'fake'|'real'
    raw_score: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    confidence_band: Mapped[str] = mapped_column(Text, nullable=False)  # 'high'|'moderate'|'low'
    is_calibrated_prob: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    preprocessing_version: Mapped[str] = mapped_column(Text, nullable=False)
    graph_construction_version: Mapped[str] = mapped_column(Text, nullable=False)
    calibration_version: Mapped[str] = mapped_column(Text, nullable=False)

    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    graph_reference: Mapped[str | None] = mapped_column(Text, nullable=True)

    propagation_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    interaction_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # pending|processing|complete|failed
    processing_status: Mapped[str] = mapped_column(Text, nullable=False)
    # private|shared
    visibility: Mapped[str] = mapped_column(Text, nullable=False, default="private")

    # Python attribute renamed to avoid colliding with
    # DeclarativeBase.metadata; the DB column itself stays "metadata"
    # per Architecture.md §4.
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
