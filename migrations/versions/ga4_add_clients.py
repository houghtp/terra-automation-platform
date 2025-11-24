"""Add GA4 clients table and link to connections.

Revision ID: ga4_add_clients
Revises: ga4_add_client_name
Create Date: 2025-11-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "ga4_add_clients"
down_revision: Union[str, Sequence[str], None] = "ga4_add_client_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ga4_clients",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_ga4_clients_tenant", "ga4_clients", ["tenant_id"])
    op.create_unique_constraint("uq_ga4_clients_tenant_name", "ga4_clients", ["tenant_id", "name"])

    op.add_column("ga4_connections", sa.Column("client_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_ga4_connections_client_id",
        "ga4_connections",
        "ga4_clients",
        ["client_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_ga4_connections_client_id", "ga4_connections", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_ga4_connections_client_id", table_name="ga4_connections")
    op.drop_constraint("fk_ga4_connections_client_id", "ga4_connections", type_="foreignkey")
    op.drop_column("ga4_connections", "client_id")
    op.drop_constraint("uq_ga4_clients_tenant_name", "ga4_clients", type_="unique")
    op.drop_index("ix_ga4_clients_tenant", table_name="ga4_clients")
    op.drop_table("ga4_clients")
