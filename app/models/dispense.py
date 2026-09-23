from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel


class Dispense(SQLModel, table=True):
    """MediStock Dispense header table recording medication fulfillment."""

    __tablename__ = "dispenses"

    id: Optional[int] = Field(default=None, primary_key=True)
    prescription_id: int = Field(foreign_key="prescriptions.id", index=True, nullable=False)
    pharmacist_id: int = Field(foreign_key="users.id", nullable=False)
    dispensed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    lines: List["DispenseLine"] = Relationship(back_populates="dispense")


class DispenseLine(SQLModel, table=True):
    """MediStock Dispense line item table recording which batch stock was drawn from."""

    __tablename__ = "dispense_lines"

    id: Optional[int] = Field(default=None, primary_key=True)
    dispense_id: int = Field(foreign_key="dispenses.id", index=True, nullable=False)
    batch_id: int = Field(foreign_key="batches.id", index=True, nullable=False)
    product_id: int = Field(foreign_key="products.id", nullable=False)
    qty: int = Field(nullable=False)

    dispense: Optional[Dispense] = Relationship(back_populates="lines")
