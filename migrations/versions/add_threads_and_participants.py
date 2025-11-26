"""Add threads and thread participants for messaging

Revision ID: add_threads_and_participants
Revises: drop_members_firm_column
Create Date: 2025-11-25
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_threads_and_participants"
down_revision = "drop_members_firm_column"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "threads",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "thread_participants",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("thread_id", sa.String(length=36), sa.ForeignKey("threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_thread_participants_thread_user_unique",
        "thread_participants",
        ["thread_id", "user_id"],
        unique=True,
    )
    op.create_index("ix_thread_participants_thread_id", "thread_participants", ["thread_id"])
    op.create_index("ix_thread_participants_user_id", "thread_participants", ["user_id"])

    # Null out legacy thread_ids that don't have a backing thread to satisfy FK
    op.execute(
        """
        UPDATE messages
        SET thread_id = NULL
        WHERE thread_id IS NOT NULL
          AND thread_id NOT IN (SELECT id FROM threads)
        """
    )

    with op.batch_alter_table("messages") as batch:
        batch.alter_column("recipient_id", existing_type=sa.String(length=36), nullable=True)
        batch.alter_column("thread_id", existing_type=sa.String(length=36), nullable=True)
        batch.create_foreign_key("fk_messages_thread_id", "threads", ["thread_id"], ["id"], ondelete="CASCADE")


def downgrade():
    with op.batch_alter_table("messages") as batch:
        batch.drop_constraint("fk_messages_thread_id", type_="foreignkey")
        batch.alter_column("recipient_id", existing_type=sa.String(length=36), nullable=False)
    op.drop_index("ix_thread_participants_thread_user_unique", table_name="thread_participants")
    op.drop_index("ix_thread_participants_thread_id", table_name="thread_participants")
    op.drop_index("ix_thread_participants_user_id", table_name="thread_participants")
    op.drop_table("thread_participants")
    op.drop_table("threads")
