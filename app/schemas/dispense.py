from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict


class DispenseCreate(BaseModel):
    """Payload for POST /api/v1/dispenses."""

    prescription_id: int


class DispenseLineRead(BaseModel):
    """Schema for individual dispense line items in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    dispense_id: int
    batch_id: int
    product_id: int
    qty: int


class DispenseRead(BaseModel):
    """Schema for full dispense responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    prescription_id: int
    pharmacist_id: int
    dispensed_at: datetime
    lines: List[DispenseLineRead]
