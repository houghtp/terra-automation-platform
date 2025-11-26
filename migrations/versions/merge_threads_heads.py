"""Merge messaging threads head with legacy head.

Revision ID: merge_threads_heads
Revises: add_threads_and_participants, c85ed9e5d323
Create Date: 2025-11-26
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "merge_threads_heads"
down_revision = ("add_threads_and_participants", "c85ed9e5d323")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
