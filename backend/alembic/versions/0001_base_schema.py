"""base schema — users, sessions, password_reset_tokens, analyses,
analysis_references, rate_limit_events (Architecture.md §4)

Revision ID: 0001
Revises:
Create Date: 2026-08-24

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # citext is required for users.email (case-insensitive uniqueness,
    # Architecture.md §4).
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="user"),
        sa.Column("email_verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_token_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "remember_device", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("used_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("input_type", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("content_reference", sa.Text(), nullable=False),
        sa.Column("verdict", sa.Text(), nullable=False),
        sa.Column("raw_score", sa.Numeric(), nullable=True),
        sa.Column("confidence_band", sa.Text(), nullable=False),
        sa.Column(
            "is_calibrated_prob", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("dataset_version", sa.Text(), nullable=True),
        sa.Column("preprocessing_version", sa.Text(), nullable=False),
        sa.Column("graph_construction_version", sa.Text(), nullable=False),
        sa.Column("calibration_version", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("explanation", postgresql.JSONB(), nullable=True),
        sa.Column("graph_reference", sa.Text(), nullable=True),
        sa.Column(
            "propagation_available", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "interaction_available", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("processing_status", sa.Text(), nullable=False),
        sa.Column("visibility", sa.Text(), nullable=False, server_default="private"),
        sa.Column(
            "metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "content_hash",
            "model_version",
            "preprocessing_version",
            "graph_construction_version",
            "calibration_version",
            name="uq_analyses_dedup_tuple",
        ),
    )
    op.create_index("ix_analyses_content_hash", "analyses", ["content_hash"])

    op.create_table(
        "analysis_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "rate_limit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("window_start", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("rate_limit_events")
    op.drop_table("analysis_references")
    op.drop_index("ix_analyses_content_hash", table_name="analyses")
    op.drop_table("analyses")
    op.drop_table("password_reset_tokens")
    op.drop_table("sessions")
    op.drop_table("users")
    # Intentionally not dropping the citext extension — Rules.md §3.4
    # "every migration is reversible" is satisfied at the schema level;
    # dropping a shared extension on downgrade risks breaking other
    # objects that may depend on it and is not required for reversibility
    # of this migration's own tables.
