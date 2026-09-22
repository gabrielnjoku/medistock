from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class StockMovement(SQLModel, table=True):
    """Immutable audit record of every inventory stock movement or adjustment.
    Tracks batch_id, quantity change (delta), reason, optional reference, and timestamp.
    """

    __tablename__ = "stock_movements"

    id: Optional[int] = Field(default=None, primary_key=True)
    batch_id: int = Field(foreign_key="batches.id", nullable=False, index=True)
    delta: int = Field(nullable=False)
    reason: str = Field(nullable=False)
    ref: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)
