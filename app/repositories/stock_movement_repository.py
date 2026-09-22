from typing import List, Optional

from sqlmodel import Session, select

from app.models.stock_movement import StockMovement


class StockMovementRepository:
    """Encapsulates all database queries targeting the `stock_movements` table."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, movement: StockMovement) -> StockMovement:
        self.db.add(movement)
        self.db.commit()
        self.db.refresh(movement)
        return movement

    def list_movements(
        self, batch_id: Optional[int] = None, limit: int = 50, offset: int = 0
    ) -> List[StockMovement]:
        statement = select(StockMovement)
        if batch_id is not None:
            statement = statement.where(StockMovement.batch_id == batch_id)
        statement = statement.order_by(StockMovement.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.exec(statement).all())
