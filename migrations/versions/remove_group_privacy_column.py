"""Remove privacy column from groups (public-by-default groups).

Revision ID: remove_group_privacy_column
Revises: merge_threads_heads
Create Date: 2025-11-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "remove_group_privacy_column"
down_revision: Union[str, Sequence[str], None] = "merge_threads_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the privacy column now that groups are public by default."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("groups")}
    if "privacy" in columns:
        with op.batch_alter_table("groups") as batch_op:
            batch_op.drop_column("privacy")


def downgrade() -> None:
    """Reintroduce privacy column (defaults to private)."""
    with op.batch_alter_table("groups") as batch_op:
        batch_op.add_column(
            sa.Column("privacy", sa.String(length=32), nullable=False, server_default="private"),
        )
