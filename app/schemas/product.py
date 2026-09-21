from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    """Request payload for POST /api/v1/products."""

    name: str = Field(min_length=1, examples=["Amoxicillin"])
    strength: str = Field(min_length=1, examples=["500mg"])


class ProductRead(BaseModel):
    """Response payload for POST /api/v1/products."""

    id: int
    name: str
    strength: str

    model_config = ConfigDict(from_attributes=True)
