from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.deps import get_db, require_role
from app.models.user import User, UserRole
from app.schemas.batch import BatchCreate, BatchRead
from app.schemas.product import ProductCreate, ProductRead
from app.services import product_service

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new product",
    description="Manager-only per brief. Adds a product with name and strength.",
    responses={
        401: {"description": "Not authenticated or token invalid"},
        403: {"description": "Caller does not hold the manager role"},
        409: {"description": "Product with name and strength already exists"},
        422: {"description": "Validation error on request body"},
    },
)
def create_product(
    payload: ProductCreate,
    current_user: User = Depends(require_role(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> ProductRead:
    """Thin route handler: parses payload, checks manager auth, delegates to product_service."""
    return product_service.create_product(db, payload)


@router.post(
    "/{id}/batches",
    response_model=BatchRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a batch to a product",
    description="Manager-only per brief. Adds a batch with batch_no, expiry_date, quantity, and cost.",
    responses={
        401: {"description": "Not authenticated or token invalid"},
        403: {"description": "Caller does not hold the manager role"},
        404: {"description": "Product not found"},
        409: {"description": "Batch number already exists for product"},
        422: {"description": "Validation error on request body"},
    },
)
def add_batch(
    id: int,
    payload: BatchCreate,
    current_user: User = Depends(require_role(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> BatchRead:
    """Thin route handler: receives batch details, checks manager auth, delegates to product_service."""
    return product_service.add_batch_to_product(db, product_id=id, payload=payload)
