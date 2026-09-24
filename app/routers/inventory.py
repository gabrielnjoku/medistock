import json
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.cache import get_cache, set_cache
from app.core.deps import get_db, require_role
from app.models.user import User, UserRole
from app.schemas.inventory import InventoryItemRead
from app.services import inventory_service

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.get(
    "",
    response_model=List[InventoryItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get current inventory stock levels",
    description="Staff accessible (manager, pharmacist, doctor). Returns products with batches and stock counts.",
    responses={
        401: {"description": "Not authenticated or token invalid"},
    },
)
def get_inventory(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    low_stock: Optional[bool] = Query(default=None),
    current_user: User = Depends(
        require_role(UserRole.MANAGER, UserRole.PHARMACIST, UserRole.DOCTOR)
    ),
    db: Session = Depends(get_db),
) -> List[InventoryItemRead]:
    """Thin route handler: checks Redis hot-read cache first, delegates DB retrieval to inventory_service on cache miss."""
    cache_key = f"cache:inventory:limit={limit}:offset={offset}:low_stock={low_stock}"
    cached_val = get_cache(cache_key)
    if cached_val is not None:
        raw_items = json.loads(cached_val)
        return [InventoryItemRead.model_validate(item) for item in raw_items]

    result = inventory_service.get_inventory(db, limit=limit, offset=offset, low_stock=low_stock)
    json_str = json.dumps([item.model_dump() for item in result], default=str)
    set_cache(cache_key, json_str, expire_seconds=300)
    return result
