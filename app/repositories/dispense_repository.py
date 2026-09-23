from typing import List, Optional
from sqlmodel import Session, select

from app.models.dispense import Dispense, DispenseLine


class DispenseRepository:
    """Encapsulates all database operations targeting the `dispenses` and `dispense_lines` tables."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, dispense_id: int) -> Optional[Dispense]:
        statement = select(Dispense).where(Dispense.id == dispense_id)
        return self.db.exec(statement).first()

    def create(self, dispense: Dispense, lines: List[DispenseLine]) -> Dispense:
        self.db.add(dispense)
        self.db.flush()
        self.db.refresh(dispense)

        for line in lines:
            line.dispense_id = dispense.id
            self.db.add(line)

        self.db.flush()
        return dispense

    def get_lines(self, dispense_id: int) -> List[DispenseLine]:
        statement = select(DispenseLine).where(DispenseLine.dispense_id == dispense_id)
        return list(self.db.exec(statement).all())
