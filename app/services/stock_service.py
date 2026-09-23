from typing import List, Optional
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.broadcaster import broadcaster
from app.models.stock_movement import StockMovement
from app.repositories.batch_repository import BatchRepository
from app.repositories.stock_movement_repository import StockMovementRepository
from app.schemas.stock_movement import StockAdjustCreate, StockMovementRead


def adjust_stock(db: Session, payload: StockAdjustCreate) -> StockMovementRead:
    """Adjust stock quantity for a batch with a reason.

    Enforces business rules:
      1. Batch check: Target batch must exist.
         Raises 404 Not Found if missing.
      2. Non-zero delta check: Delta cannot be 0.
         Raises 422 Unprocessable Entity if delta is zero.
      3. Non-negative stock balance check: batch.qty_on_hand + delta >= 0.
         Raises 422 Unprocessable Entity if adjustment results in negative stock.
      4. Single transaction: Updates batch qty_on_hand and creates StockMovement record together.
      5. Live alert stream: Publishes stock_change event to the broadcaster.
    """
    if payload.delta == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Stock adjustment delta cannot be zero",
        )

    batch_repo = BatchRepository(db)
    batch = batch_repo.get_by_id(payload.batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch with id {payload.batch_id} not found",
        )

    new_qty = batch.qty_on_hand + payload.delta
    if new_qty < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Insufficient stock: current qty is {batch.qty_on_hand}, cannot adjust by {payload.delta}",
        )

    batch.qty_on_hand = new_qty
    db.add(batch)

    movement = StockMovement(
        batch_id=payload.batch_id,
        delta=payload.delta,
        reason=payload.reason,
        ref=payload.ref,
    )
    movement_repo = StockMovementRepository(db)
    created_movement = movement_repo.create(movement)

    # Publish SSE alert event to active stream subscribers
    broadcaster.publish({
        "event": "stock_change",
        "batch_id": payload.batch_id,
        "product_id": batch.product_id,
        "delta": payload.delta,
        "qty_on_hand": new_qty,
        "reason": payload.reason,
        "timestamp": created_movement.created_at.isoformat() if created_movement.created_at else None,
    })

    return StockMovementRead.model_validate(created_movement)


def get_stock_movements(
    db: Session, batch_id: Optional[int] = None, limit: int = 50, offset: int = 0
) -> List[StockMovementRead]:
    """Retrieve audit log of stock movements."""
    movement_repo = StockMovementRepository(db)
    movements = movement_repo.list_movements(batch_id=batch_id, limit=limit, offset=offset)
    return [StockMovementRead.model_validate(m) for m in movements]
