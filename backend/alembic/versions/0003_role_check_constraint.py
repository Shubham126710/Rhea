"""users.role CHECK constraint

Found in audit: role has always been documented as one of
'user'/'admin'/'research' (PRD Batch C, comment in user.py), but
nothing enforced that at the database level — only application code
ever happened to write 'user'. This makes the documented invariant
enforced rather than implicit.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-28

"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_users_role_valid",
        "users",
        "role IN ('user', 'admin', 'research')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role_valid", "users", type_="check")
