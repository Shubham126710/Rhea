"""auth integrity constraints and throttle-query index

Found in adversarial security/performance review of Phase 1:
- sessions.session_token_hash and password_reset_tokens.token_hash
  had no uniqueness enforced at the DB level. Collision probability
  with 256-bit tokens is negligible in practice, but the application
  code (get_user_by_session_token) already assumes uniqueness via
  scalar_one_or_none(); this migration makes that assumption an
  enforced invariant instead of an implicit one.
- rate_limit_events had no index supporting the (kind, window_start)
  query every login/signup throttle check runs, meaning that query
  sequentially scans the whole table as it grows.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-28

"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_sessions_session_token_hash",
        "sessions",
        ["session_token_hash"],
        unique=True,
    )
    op.create_index(
        "uq_password_reset_tokens_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_rate_limit_events_kind_window_start",
        "rate_limit_events",
        ["kind", "window_start"],
    )


def downgrade() -> None:
    op.drop_index("ix_rate_limit_events_kind_window_start", table_name="rate_limit_events")
    op.drop_index("uq_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("uq_sessions_session_token_hash", table_name="sessions")
