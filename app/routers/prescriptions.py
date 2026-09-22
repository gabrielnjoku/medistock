from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.deps import get_db, require_role
from app.models.user import User, UserRole
from app.schemas.prescription import PrescriptionCreate, PrescriptionRead
from app.services import prescription_service

router = APIRouter(prefix="/api/v1/prescriptions", tags=["prescriptions"])


@router.post(
    "",
    response_model=PrescriptionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new prescription",
    description="Doctor-only per brief. Creates a prescription with line items for a patient.",
    responses={
        401: {"description": "Not authenticated or token invalid"},
        403: {"description": "Caller does not hold the doctor role"},
        422: {"description": "Validation error on request body or non-existent product id"},
    },
)
def create_prescription(
    payload: PrescriptionCreate,
    current_user: User = Depends(require_role(UserRole.DOCTOR)),
    db: Session = Depends(get_db),
) -> PrescriptionRead:
    """Thin route handler: parses payload, checks doctor auth, delegates to prescription_service."""
    return prescription_service.create_prescription(db, doctor_id=current_user.id, payload=payload)


@router.get(
    "/{id}",
    response_model=PrescriptionRead,
    status_code=status.HTTP_200_OK,
    summary="Get prescription by ID",
    description="Staff accessible (doctor, pharmacist, manager). Retrieves prescription details.",
    responses={
        401: {"description": "Not authenticated or token invalid"},
        404: {"description": "Prescription not found"},
    },
)
def get_prescription(
    id: int,
    current_user: User = Depends(
        require_role(UserRole.DOCTOR, UserRole.PHARMACIST, UserRole.MANAGER)
    ),
    db: Session = Depends(get_db),
) -> PrescriptionRead:
    """Thin route handler: validates staff auth, delegates lookup to prescription_service."""
    return prescription_service.get_prescription_by_id(db, prescription_id=id)
