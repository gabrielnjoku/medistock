from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class DeliveryItemPayload(BaseModel):
    """Line item in a supplier delivery webhook payload."""

    product_id: int = Field(gt=0, examples=[1])
    batch_no: str = Field(min_length=1, examples=["SUP-B9921"])
    expiry_date: date = Field(examples=["2027-12-31"])
    qty: int = Field(gt=0, examples=[500])
    cost: float = Field(gt=0, examples=[10.50])


class DeliveryWebhookPayload(BaseModel):
    """Payload sent to POST /api/v1/webhooks/deliveries by supplier systems."""

    event_id: str = Field(min_length=1, examples=["evt_del_99812"])
    type: str = Field(default="delivery.dispatched", examples=["delivery.dispatched"])
    reference: str = Field(min_length=1, examples=["PO-2026-001"])
    items: List[DeliveryItemPayload] = Field(default_factory=list)


class WebhookResponse(BaseModel):
    """Response returned by POST /api/v1/webhooks/deliveries."""

    status: str = Field(examples=["processed", "duplicate_ignored", "orphan_logged"])
    event_id: str
    message: Optional[str] = None
