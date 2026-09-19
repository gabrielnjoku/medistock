from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.deps import get_db
from app.schemas.user import UserCreate, UserRead
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=201,
    summary="Register a new staff or supplier account",
    description="Manager-only per the brief. require_role isn't applied yet — "
    "see the TODO in app/services/auth_service.py before this route is viva-ready.",
    responses={
        403: {"description": "Caller is not a manager"},
        409: {"description": "Email already registered"},
        422: {"description": "Validation error"},
    },
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    # Thin on purpose: parse the request (FastAPI + Pydantic did that
    # above), call one service function, return what it gives back.
    # No business rules belong in this function body.
    return auth_service.register_user(db, payload)
