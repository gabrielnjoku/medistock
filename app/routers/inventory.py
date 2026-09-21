from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

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
    """Thin route handler: validates staff auth and query parameters, delegates to inventory_service."""
    return inventory_service.get_inventory(db, limit=limit, offset=offset, low_stock=low_stock)
