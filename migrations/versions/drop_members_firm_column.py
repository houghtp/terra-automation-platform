"""Drop firm column from members (use partner instead).

Revision ID: drop_members_firm_column
Revises: b3fb10b
Create Date: 2025-11-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "drop_members_firm_column"
down_revision: Union[str, Sequence[str], None] = "b3fb10b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("members") as batch:
        batch.drop_column("firm")


def downgrade() -> None:
    with op.batch_alter_table("members") as batch:
        batch.add_column(sa.Column("firm", sa.String(length=255), nullable=True))
