from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StockAdjustCreate(BaseModel):
    """Request payload for POST /api/v1/stock/adjust."""

    batch_id: int = Field(gt=0, examples=[1])
    delta: int = Field(examples=[-5], description="Stock quantity change (positive or negative, non-zero)")
    reason: str = Field(min_length=1, examples=["Damaged during stock check"])
    ref: Optional[str] = Field(default=None, examples=["ADJ-2026-001"])


class StockMovementRead(BaseModel):
    """Response payload for stock movement log records."""

    id: int
    batch_id: int
    delta: int
    reason: str
    ref: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
