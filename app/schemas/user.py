from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    """What the client sends to POST /api/v1/auth/register. Separate from the
    User table model on purpose — the request has a plaintext
    `password`, the table has `password_hash`, and they should never be
    the same class.
    """

    email: EmailStr = Field(examples=["pharmacist@medistock.com"])
    password: str = Field(min_length=8, examples=["SecurePass123!"])
    role: UserRole = Field(examples=[UserRole.PHARMACIST])


class UserRead(BaseModel):
    """What the API returns. No password_hash field exists here at
    all — it's not "hidden", it's structurally impossible to leak it
    through this schema, which is what response_model is for.
    """

    id: int
    email: EmailStr
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """Request body for POST /api/v1/auth/login."""

    email: EmailStr = Field(examples=["pharmacist@medistock.com"])
    password: str = Field(examples=["SecurePass123!"])


class Token(BaseModel):
    """Bearer token response returned by POST /api/v1/auth/login."""

    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = Field(default="bearer", examples=["bearer"])
