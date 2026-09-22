from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Prescription(SQLModel, table=True):
    """Prescription written by a doctor for a patient.
    Stores status ('pending', 'dispensed', 'cancelled') and doctor FK.
    """

    __tablename__ = "prescriptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    patient_name: str = Field(nullable=False)
    doctor_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    status: str = Field(default="pending", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class PrescriptionLine(SQLModel, table=True):
    """Line item in a prescription detailing product and quantity ordered."""

    __tablename__ = "prescription_lines"

    id: Optional[int] = Field(default=None, primary_key=True)
    prescription_id: int = Field(foreign_key="prescriptions.id", nullable=False, index=True)
    product_id: int = Field(foreign_key="products.id", nullable=False, index=True)
    qty: int = Field(nullable=False)
