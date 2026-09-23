import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.core.broadcaster import broadcaster
from app.core.deps import get_current_user, get_db, require_role
from app.models.user import User, UserRole
from app.schemas.stock_movement import StockAdjustCreate, StockMovementRead
from app.services import stock_service

router = APIRouter(prefix="/api/v1/stock", tags=["stock"])


@router.get(
    "/alerts/stream",
    summary="Subscribe to live SSE stock alert stream",
    description="Publishes Server-Sent Events (SSE) for stock state changes with a 15-second heartbeat.",
    responses={
        200: {"description": "Connected to SSE stock alert stream", "content": {"text/event-stream": {}}},
        401: {"description": "Not authenticated or token invalid"},
    },
)
async def stream_stock_alerts(
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Streams real-time stock state change notifications over SSE with 15s heartbeats."""

    async def event_generator():
        queue = broadcaster.subscribe()
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/adjust",
    response_model=StockMovementRead,
    status_code=status.HTTP_201_CREATED,
    summary="Adjust stock level for a batch",
    description="Pharmacist-only per brief. Adjusts stock quantity for a batch with a reason.",
    responses={
        401: {"description": "Not authenticated or token invalid"},
        403: {"description": "Caller does not hold the pharmacist role"},
        404: {"description": "Batch not found"},
        422: {"description": "Validation error or negative resulting stock balance"},
    },
)
def adjust_stock(
    payload: StockAdjustCreate,
    current_user: User = Depends(require_role(UserRole.PHARMACIST)),
    db: Session = Depends(get_db),
) -> StockMovementRead:
    """Thin route handler: validates pharmacist auth, delegates adjustment to stock_service."""
    return stock_service.adjust_stock(db, payload)


@router.get(
    "/movements",
    response_model=List[StockMovementRead],
    status_code=status.HTTP_200_OK,
    summary="Get stock movement logs",
    description="Manager-only per brief. Retrieves audit log of inventory stock movements.",
    responses={
        401: {"description": "Not authenticated or token invalid"},
        403: {"description": "Caller does not hold the manager role"},
    },
)
def get_stock_movements(
    batch_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_role(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> List[StockMovementRead]:
    """Thin route handler: validates manager auth, delegates retrieval to stock_service."""
    return stock_service.get_stock_movements(db, batch_id=batch_id, limit=limit, offset=offset)
