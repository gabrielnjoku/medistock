from typing import Optional

from sqlmodel import Session, select

from app.models.processed_event import ProcessedEvent


class ProcessedEventRepository:
    """Encapsulates all database queries targeting the `processed_events` table."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_event_id(self, event_id: str) -> Optional[ProcessedEvent]:
        statement = select(ProcessedEvent).where(ProcessedEvent.event_id == event_id)
        return self.db.exec(statement).first()

    def create(self, event: ProcessedEvent) -> ProcessedEvent:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
