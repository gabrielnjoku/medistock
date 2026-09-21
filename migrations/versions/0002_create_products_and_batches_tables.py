"""create products and batches tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-21

Matches the Day 4 ERD requirements:
- products table with UNIQUE(name, strength)
- batches table with FK to products.id, UNIQUE(product_id, batch_no), and index on expiry_date for FEFO.
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("strength", sa.String(), nullable=False),
        sa.UniqueConstraint("name", "strength", name="uq_product_name_strength"),
    )
    op.create_index("ix_products_name", "products", ["name"])

    op.create_table(
        "batches",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_no", sa.String(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("qty_on_hand", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost", sa.Float(), nullable=False),
        sa.UniqueConstraint("product_id", "batch_no", name="uq_batch_product_batch_no"),
    )
    op.create_index("ix_batches_product_id", "batches", ["product_id"])
    op.create_index("ix_batches_expiry_date", "batches", ["expiry_date"])


def downgrade() -> None:
    op.drop_index("ix_batches_expiry_date", table_name="batches")
    op.drop_index("ix_batches_product_id", table_name="batches")
    op.drop_table("batches")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_table("products")
