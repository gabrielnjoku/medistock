from typing import Optional
from fastapi import APIRouter, Depends, Header, Request, status
from sqlmodel import Session

from app.core.deps import get_db, require_role
from app.models.user import User, UserRole
from app.schemas.dispense import DispenseCreate, DispenseRead
from app.services import dispense_service

router = APIRouter(prefix="/api/v1/dispenses", tags=["dispenses"])


@router.post(
    "",
    response_model=DispenseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Dispense prescription medications (Idempotent, FEFO)",
    description=(
        "Pharmacist-only per brief. Dispenses ordered prescription items strictly "
        "from non-expired batches in FEFO order (First Expired, First Out) with "
        "row-level locking (SELECT ... FOR UPDATE) and Idempotency-Key retry-safety."
    ),
    responses={
        201: {"description": "Dispense recorded successfully"},
        401: {"description": "Not authenticated or token invalid"},
        403: {"description": "Caller does not hold the pharmacist role"},
        404: {"description": "Prescription not found"},
        409: {"description": "Insufficient non-expired stock for requested items"},
        422: {"description": "Missing/reused Idempotency-Key header or invalid request payload"},
    },
)
def create_dispense(
    request: Request,
    payload: DispenseCreate,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(require_role(UserRole.PHARMACIST)),
    db: Session = Depends(get_db),
) -> DispenseRead:
    """Thin route handler: validates pharmacist auth & Idempotency-Key header, delegates logic to dispense_service."""
    return dispense_service.dispense_prescription(
        db=db,
        idempotency_key=idempotency_key or "",
        path=request.url.path,
        pharmacist_id=current_user.id,
        payload=payload,
    )
