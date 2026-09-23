"""create dispenses and idempotency_keys tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-23

Matches Day 8 requirements:
- dispenses header table
- dispense_lines item table
- idempotency_keys response cache table
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dispenses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("prescription_id", sa.BigInteger(), sa.ForeignKey("prescriptions.id"), nullable=False),
        sa.Column("pharmacist_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("dispensed_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_dispenses_prescription_id", "dispenses", ["prescription_id"])

    op.create_table(
        "dispense_lines",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("dispense_id", sa.BigInteger(), sa.ForeignKey("dispenses.id"), nullable=False),
        sa.Column("batch_id", sa.BigInteger(), sa.ForeignKey("batches.id"), nullable=False),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
    )
    op.create_index("ix_dispense_lines_dispense_id", "dispense_lines", ["dispense_id"])
    op.create_index("ix_dispense_lines_batch_id", "dispense_lines", ["batch_id"])

    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("request_hash", sa.String(), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_index("ix_dispense_lines_batch_id", table_name="dispense_lines")
    op.drop_index("ix_dispense_lines_dispense_id", table_name="dispense_lines")
    op.drop_table("dispense_lines")
    op.drop_index("ix_dispenses_prescription_id", table_name="dispenses")
    op.drop_table("dispenses")
