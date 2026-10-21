"""add user roles and document soft delete

Revision ID: 3b8d5f1a6c20
Revises: 7f3c2a9d1e84
Create Date: 2026-10-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "3b8d5f1a6c20"
down_revision: Union[str, Sequence[str], None] = "7f3c2a9d1e84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role_enum = postgresql.ENUM(
    "USER",
    "ADMIN",
    name="user_role",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    user_role_enum.create(
        op.get_bind(),
        checkfirst=False,
    )
    op.add_column(
        "users",
        sa.Column(
            "role",
            user_role_enum,
            server_default=sa.text("'USER'"),
            nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("documents", "deleted_at")
    op.drop_column("users", "role")
    user_role_enum.drop(
        op.get_bind(),
        checkfirst=False,
    )
