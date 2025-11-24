"""Add client_name to GA4 connections.

Revision ID: ga4_add_client_name
Revises: merge_ga4_heads_post_expand
Create Date: 2025-11-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "ga4_add_client_name"
down_revision: Union[str, Sequence[str], None] = "merge_ga4_heads_post_expand"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ga4_connections", sa.Column("client_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("ga4_connections", "client_name")
