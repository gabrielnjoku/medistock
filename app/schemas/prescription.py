from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class PrescriptionLineCreate(BaseModel):
    """Line item in a prescription creation request."""

    product_id: int = Field(gt=0, examples=[1])
    qty: int = Field(gt=0, examples=[20])


class PrescriptionCreate(BaseModel):
    """Request payload for POST /api/v1/prescriptions."""

    patient_name: str = Field(min_length=1, examples=["John Doe"])
    lines: List[PrescriptionLineCreate] = Field(min_length=1)


class PrescriptionLineRead(BaseModel):
    """Response model for a prescription line item."""

    id: int
    prescription_id: int
    product_id: int
    qty: int

    model_config = ConfigDict(from_attributes=True)


class PrescriptionRead(BaseModel):
    """Response payload for prescription endpoints."""

    id: int
    patient_name: str
    doctor_id: int
    status: str
    created_at: datetime
    lines: List[PrescriptionLineRead]

    model_config = ConfigDict(from_attributes=True)
