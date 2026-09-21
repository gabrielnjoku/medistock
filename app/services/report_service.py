from datetime import date, timedelta
from typing import List
from sqlmodel import Session

from app.repositories.batch_repository import BatchRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.report import LowStockReportItem, NearExpiryReportItem


def get_low_stock_report(db: Session, threshold: int = 10) -> List[LowStockReportItem]:
    """Generates low-stock report for products whose total stock <= threshold."""
    product_repo = ProductRepository(db)
    batch_repo = BatchRepository(db)

    products = product_repo.list_products(limit=1000, offset=0)
    report: List[LowStockReportItem] = []

    for product in products:
        batches = batch_repo.get_batches_by_product(product.id)
        total_qty = sum(b.qty_on_hand for b in batches)
        if total_qty <= threshold:
            report.append(
                LowStockReportItem(
                    product_id=product.id,
                    name=product.name,
                    strength=product.strength,
                    total_qty_on_hand=total_qty,
                )
            )

    return report


def get_near_expiry_report(db: Session, days: int = 30) -> List[NearExpiryReportItem]:
    """Generates report of batches expiring within specified days from today."""
    batch_repo = BatchRepository(db)
    product_repo = ProductRepository(db)

    today = date.today()
    cutoff_date = today + timedelta(days=days)
    batches = batch_repo.get_near_expiry_batches(cutoff_date)

    report: List[NearExpiryReportItem] = []
    for batch in batches:
        product = product_repo.get_by_id(batch.product_id)
        if product is None:
            continue
        days_to_expiry = (batch.expiry_date - today).days
        report.append(
            NearExpiryReportItem(
                batch_id=batch.id,
                product_id=product.id,
                product_name=product.name,
                strength=product.strength,
                batch_no=batch.batch_no,
                expiry_date=batch.expiry_date,
                qty_on_hand=batch.qty_on_hand,
                days_to_expiry=days_to_expiry,
            )
        )

    return report
