import enum
from typing import Optional

from sqlmodel import Field, SQLModel


class UserRole(str, enum.Enum):
    """The brief's four roles. A real enum, not a bare string field —
    a typo in a role name fails at import time instead of silently
    passing validation and failing a require_role check at 3am.
    """

    PHARMACIST = "pharmacist"
    DOCTOR = "doctor"
    MANAGER = "manager"
    SUPPLIER = "supplier"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    password_hash: str = Field(nullable=False)
    role: UserRole = Field(nullable=False)
