from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class Product(SQLModel, table=True):
    """MediStock Product entity representing a drug name and strength.
    Unique constraint on (name, strength) guarantees no duplicate drug entries.
    """

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("name", "strength", name="uq_product_name_strength"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, nullable=False)
    strength: str = Field(nullable=False)
