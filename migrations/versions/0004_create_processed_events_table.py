"""create processed_events table

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-22

Matches Day 6 requirements:
- processed_events table with UNIQUE(event_id) for webhook deduplication.
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "processed_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_processed_events_event_id", "processed_events", ["event_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_processed_events_event_id", table_name="processed_events")
    op.drop_table("processed_events")
