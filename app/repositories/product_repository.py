from typing import List, Optional

from sqlmodel import Session, select

from app.models.product import Product


class ProductRepository:
    """Encapsulates all database queries targeting the `products` table.
    Ensures zero raw queries leak into routers or service layers.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: int) -> Optional[Product]:
        statement = select(Product).where(Product.id == product_id)
        return self.db.exec(statement).first()

    def get_by_name_and_strength(self, name: str, strength: str) -> Optional[Product]:
        statement = select(Product).where(Product.name == name, Product.strength == strength)
        return self.db.exec(statement).first()

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def list_products(self, limit: int = 50, offset: int = 0) -> List[Product]:
        statement = select(Product).offset(offset).limit(limit)
        return list(self.db.exec(statement).all())
