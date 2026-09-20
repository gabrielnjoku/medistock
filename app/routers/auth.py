from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.deps import get_db, require_role
from app.models.user import User, UserRole
from app.schemas.user import Token, UserCreate, UserLogin, UserRead
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new staff or supplier account",
    description=(
        "Manager-only per project brief. Creates a user account with a bcrypt-hashed "
        "password and designated role (pharmacist, doctor, manager, supplier)."
    ),
    responses={
        401: {"description": "Not authenticated or token invalid"},
        403: {"description": "Caller does not hold the manager role"},
        409: {"description": "Email is already registered in MediStock"},
        422: {"description": "Validation error on request body"},
    },
)
def register(
    payload: UserCreate,
    current_user: User = Depends(require_role(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> UserRead:
    """Thin route handler: parses validated payload and delegates business logic
    to auth_service.register_user.
    """
    return auth_service.register_user(db, payload)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User login and JWT token issuance",
    description="Public endpoint. Verifies email and password, returning a signed JWT access token.",
    responses={
        401: {"description": "Invalid email or password"},
        422: {"description": "Validation error on request body"},
    },
)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Thin route handler: receives credentials, delegates authentication and token
    generation to auth_service.authenticate_user.
    """
    return auth_service.authenticate_user(db, payload)
