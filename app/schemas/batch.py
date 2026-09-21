from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class BatchCreate(BaseModel):
    """Request payload for POST /api/v1/products/{id}/batches."""

    batch_no: str = Field(min_length=1, examples=["B12345"])
    expiry_date: date = Field(examples=["2027-03-31"])
    qty_on_hand: int = Field(ge=0, examples=[100])
    cost: float = Field(gt=0, examples=[15.50])


class BatchRead(BaseModel):
    """Response payload for batch endpoints."""

    id: int
    product_id: int
    batch_no: str
    expiry_date: date
    qty_on_hand: int
    cost: float

    model_config = ConfigDict(from_attributes=True)
