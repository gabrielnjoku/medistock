from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ProcessedEvent(SQLModel, table=True):
    """Tracks unique event IDs processed by webhook consumers.
    Guarantees idempotency: any duplicate event_id is recognized and ignored.
    """

    __tablename__ = "processed_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: str = Field(unique=True, index=True, nullable=False)
    reference: str = Field(nullable=False)
    processed_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
