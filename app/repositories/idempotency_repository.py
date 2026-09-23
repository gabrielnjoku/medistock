from typing import Optional
from sqlmodel import Session, select

from app.models.idempotency_key import IdempotencyKey


class IdempotencyRepository:
    """Encapsulates all database queries targeting the `idempotency_keys` table."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_key(self, key: str) -> Optional[IdempotencyKey]:
        statement = select(IdempotencyKey).where(IdempotencyKey.key == key)
        return self.db.exec(statement).first()

    def create(self, record: IdempotencyKey) -> IdempotencyKey:
        self.db.add(record)
        self.db.flush()
        return record
