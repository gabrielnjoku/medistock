from typing import List, Optional

from sqlmodel import Session, select

from app.models.prescription import Prescription, PrescriptionLine


class PrescriptionRepository:
    """Encapsulates all database queries targeting `prescriptions` and `prescription_lines`."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, prescription_id: int) -> Optional[Prescription]:
        statement = select(Prescription).where(Prescription.id == prescription_id)
        return self.db.exec(statement).first()

    def get_lines(self, prescription_id: int) -> List[PrescriptionLine]:
        statement = select(PrescriptionLine).where(PrescriptionLine.prescription_id == prescription_id)
        return list(self.db.exec(statement).all())

    def create(self, prescription: Prescription, lines: List[PrescriptionLine]) -> Prescription:
        """Persists a prescription and its lines within a single transaction."""
        self.db.add(prescription)
        self.db.commit()
        self.db.refresh(prescription)

        for line in lines:
            line.prescription_id = prescription.id
            self.db.add(line)

        self.db.commit()
        return prescription
