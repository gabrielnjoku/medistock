from fastapi import HTTPException, status
from sqlmodel import Session

from app.models.prescription import Prescription, PrescriptionLine
from app.repositories.product_repository import ProductRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.schemas.prescription import (
    PrescriptionCreate,
    PrescriptionLineRead,
    PrescriptionRead,
)


def create_prescription(db: Session, doctor_id: int, payload: PrescriptionCreate) -> PrescriptionRead:
    """Create a new prescription written by a doctor.

    Enforces business rules:
      1. Product validation: Every ordered product_id must exist in the database.
         Raises 422 Unprocessable Entity if an ordered product does not exist.
      2. Single transaction persistence: Creates prescription header and lines together.
    """
    product_repo = ProductRepository(db)
    for line in payload.lines:
        if product_repo.get_by_id(line.product_id) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Product with id {line.product_id} not found",
            )

    prescription = Prescription(
        patient_name=payload.patient_name,
        doctor_id=doctor_id,
        status="pending",
    )
    lines = [PrescriptionLine(product_id=line.product_id, qty=line.qty) for line in payload.lines]

    rx_repo = PrescriptionRepository(db)
    created_rx = rx_repo.create(prescription, lines)
    created_lines = rx_repo.get_lines(created_rx.id)

    line_reads = [PrescriptionLineRead.model_validate(l) for l in created_lines]
    return PrescriptionRead(
        id=created_rx.id,
        patient_name=created_rx.patient_name,
        doctor_id=created_rx.doctor_id,
        status=created_rx.status,
        created_at=created_rx.created_at,
        lines=line_reads,
    )


def get_prescription_by_id(db: Session, prescription_id: int) -> PrescriptionRead:
    """Retrieve prescription by ID with line items.

    Raises 404 Not Found if prescription does not exist.
    """
    rx_repo = PrescriptionRepository(db)
    prescription = rx_repo.get_by_id(prescription_id)
    if prescription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription with id {prescription_id} not found",
        )

    lines = rx_repo.get_lines(prescription.id)
    line_reads = [PrescriptionLineRead.model_validate(l) for l in lines]
    return PrescriptionRead(
        id=prescription.id,
        patient_name=prescription.patient_name,
        doctor_id=prescription.doctor_id,
        status=prescription.status,
        created_at=prescription.created_at,
        lines=line_reads,
    )
