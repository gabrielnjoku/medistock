from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserCreate(BaseModel):
    """What the client sends to POST /auth/register. Separate from the
    User table model on purpose — the request has a plaintext
    `password`, the table has `password_hash`, and they should never be
    the same class.
    """

    email: EmailStr
    password: str
    role: UserRole


class UserRead(BaseModel):
    """What the API returns. No password_hash field exists here at
    all — it's not "hidden", it's structurally impossible to leak it
    through this schema, which is what response_model is for.
    """

    id: int
    email: EmailStr
    role: UserRole

    class Config:
        from_attributes = True
