"""create prescriptions and stock_movements tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-22

Matches Day 5 requirements:
- prescriptions and prescription_lines tables
- stock_movements table for stock adjustment logging
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Prescriptions
    op.create_table(
        "prescriptions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("patient_name", sa.String(), nullable=False),
        sa.Column("doctor_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_prescriptions_doctor_id", "prescriptions", ["doctor_id"])

    # Prescription Lines
    op.create_table(
        "prescription_lines",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("prescription_id", sa.BigInteger(), sa.ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
    )
    op.create_index("ix_prescription_lines_prescription_id", "prescription_lines", ["prescription_id"])
    op.create_index("ix_prescription_lines_product_id", "prescription_lines", ["product_id"])

    # Stock Movements
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", sa.BigInteger(), sa.ForeignKey("batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("ref", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_stock_movements_batch_id", "stock_movements", ["batch_id"])
    op.create_index("ix_stock_movements_created_at", "stock_movements", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_stock_movements_created_at", table_name="stock_movements")
    op.drop_index("ix_stock_movements_batch_id", table_name="stock_movements")
    op.drop_table("stock_movements")

    op.drop_index("ix_prescription_lines_product_id", table_name="prescription_lines")
    op.drop_index("ix_prescription_lines_prescription_id", table_name="prescription_lines")
    op.drop_table("prescription_lines")

    op.drop_index("ix_prescriptions_doctor_id", table_name="prescriptions")
    op.drop_table("prescriptions")
