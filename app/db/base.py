"""Import every SQLModel table class here so Alembic's metadata (and
anything else that needs the full schema in one place) sees it. Add one
line per new model as the schema grows — miss one and Alembic won't
know that table exists.
"""

from sqlmodel import SQLModel  # noqa: F401

from app.models.batch import Batch  # noqa: F401
from app.models.prescription import Prescription, PrescriptionLine  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.stock_movement import StockMovement  # noqa: F401
from app.models.user import User  # noqa: F401
