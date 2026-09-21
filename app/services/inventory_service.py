from typing import List, Optional
from sqlmodel import Session

from app.repositories.batch_repository import BatchRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.batch import BatchRead
from app.schemas.inventory import InventoryItemRead


def get_inventory(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    low_stock: Optional[bool] = None,
) -> List[InventoryItemRead]:
    """Retrieve list of products with their batches and stock summaries.

    Supports limit/offset pagination and low_stock filtering.
    """
    product_repo = ProductRepository(db)
    batch_repo = BatchRepository(db)

    products = product_repo.list_products(limit=limit, offset=offset)
    items: List[InventoryItemRead] = []

    for product in products:
        batches = batch_repo.get_batches_by_product(product.id)
        total_qty = sum(b.qty_on_hand for b in batches)

        if low_stock is True and total_qty > 10:
            continue

        batch_reads = [BatchRead.model_validate(b) for b in batches]
        items.append(
            InventoryItemRead(
                product_id=product.id,
                name=product.name,
                strength=product.strength,
                total_qty_on_hand=total_qty,
                batches=batch_reads,
            )
        )

    return items
