from typing import List

from pydantic import BaseModel, ConfigDict

from app.schemas.batch import BatchRead


class InventoryItemRead(BaseModel):
    """Response model for GET /api/v1/inventory."""

    product_id: int
    name: str
    strength: str
    total_qty_on_hand: int
    batches: List[BatchRead]

    model_config = ConfigDict(from_attributes=True)
