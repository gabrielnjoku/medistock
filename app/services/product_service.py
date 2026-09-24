from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.cache import invalidate_cache_pattern
from app.models.batch import Batch
from app.models.product import Product
from app.repositories.batch_repository import BatchRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.batch import BatchCreate, BatchRead
from app.schemas.product import ProductCreate, ProductRead


def create_product(db: Session, payload: ProductCreate) -> ProductRead:
    """Create a new product with name and strength.

    Enforces business rules:
      1. Duplicate check: (name, strength) must be unique.
         Raises 409 Conflict if already exists.
      2. Persistence delegated to ProductRepository.
      3. Invalidation: Clears cached inventory reads.
    """
    product_repo = ProductRepository(db)
    existing_product = product_repo.get_by_name_and_strength(payload.name, payload.strength)
    if existing_product is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product with this name and strength already exists",
        )

    product = Product(name=payload.name, strength=payload.strength)
    created_product = product_repo.create(product)
    invalidate_cache_pattern("cache:inventory:*")
    return ProductRead.model_validate(created_product)


def add_batch_to_product(db: Session, product_id: int, payload: BatchCreate) -> BatchRead:
    """Add a new batch with expiry date and stock level to a product.

    Enforces business rules:
      1. Product existence check: Product with product_id must exist.
         Raises 404 Not Found if missing.
      2. Duplicate batch check: (product_id, batch_no) must be unique.
         Raises 409 Conflict if batch number already exists for product.
      3. Persistence delegated to BatchRepository.
      4. Invalidation: Clears cached inventory and near-expiry report reads.
    """
    product_repo = ProductRepository(db)
    product = product_repo.get_by_id(product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )

    batch_repo = BatchRepository(db)
    existing_batch = batch_repo.get_by_product_and_batch_no(product_id, payload.batch_no)
    if existing_batch is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Batch '{payload.batch_no}' already exists for product {product_id}",
        )

    batch = Batch(
        product_id=product_id,
        batch_no=payload.batch_no,
        expiry_date=payload.expiry_date,
        qty_on_hand=payload.qty_on_hand,
        cost=payload.cost,
    )
    created_batch = batch_repo.create(batch)
    invalidate_cache_pattern("cache:inventory:*")
    invalidate_cache_pattern("cache:reports:near-expiry:*")
    return BatchRead.model_validate(created_batch)
