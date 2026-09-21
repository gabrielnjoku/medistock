from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class Batch(SQLModel, table=True):
    """MediStock Batch entity. Stock is counted per batch, not per drug.
    Indexed on expiry_date for efficient FEFO (First-Expired, First-Out) queries.
    Unique constraint on (product_id, batch_no) ensures unique batch numbers per product.
    """

    __tablename__ = "batches"
    __table_args__ = (
        UniqueConstraint("product_id", "batch_no", name="uq_batch_product_batch_no"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", nullable=False, index=True)
    batch_no: str = Field(nullable=False)
    expiry_date: date = Field(index=True, nullable=False)
    qty_on_hand: int = Field(default=0, nullable=False)
    cost: float = Field(nullable=False)
