from datetime import date
from typing import List, Optional

from sqlmodel import Session, select

from app.models.batch import Batch


class BatchRepository:
    """Encapsulates all database queries targeting the `batches` table.
    Indexes on expiry_date are leveraged for fast near-expiry retrieval.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, batch_id: int) -> Optional[Batch]:
        statement = select(Batch).where(Batch.id == batch_id)
        return self.db.exec(statement).first()

    def get_by_product_and_batch_no(self, product_id: int, batch_no: str) -> Optional[Batch]:
        statement = select(Batch).where(Batch.product_id == product_id, Batch.batch_no == batch_no)
        return self.db.exec(statement).first()

    def create(self, batch: Batch) -> Batch:
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def get_batches_by_product(self, product_id: int) -> List[Batch]:
        statement = select(Batch).where(Batch.product_id == product_id).order_by(Batch.expiry_date.asc())
        return list(self.db.exec(statement).all())

    def get_near_expiry_batches(self, cutoff_date: date) -> List[Batch]:
        statement = (
            select(Batch)
            .where(Batch.expiry_date <= cutoff_date, Batch.qty_on_hand > 0)
            .order_by(Batch.expiry_date.asc())
        )
        return list(self.db.exec(statement).all())
