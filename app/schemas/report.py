from datetime import date

from pydantic import BaseModel, ConfigDict


class LowStockReportItem(BaseModel):
    """Response item for GET /api/v1/reports/low-stock."""

    product_id: int
    name: str
    strength: str
    total_qty_on_hand: int

    model_config = ConfigDict(from_attributes=True)


class NearExpiryReportItem(BaseModel):
    """Response item for GET /api/v1/reports/near-expiry."""

    batch_id: int
    product_id: int
    product_name: str
    strength: str
    batch_no: str
    expiry_date: date
    qty_on_hand: int
    days_to_expiry: int

    model_config = ConfigDict(from_attributes=True)
