from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class IdempotencyKey(SQLModel, table=True):
    """Stores cached response payloads associated with Idempotency-Key headers."""

    __tablename__ = "idempotency_keys"

    key: str = Field(primary_key=True)
    request_hash: str = Field(nullable=False)
    response_code: int = Field(nullable=False)
    response_body: str = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
