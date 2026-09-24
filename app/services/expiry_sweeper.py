import logging
from datetime import date, timedelta
from typing import Dict, List
from sqlmodel import Session

from app.core.broadcaster import broadcaster
from app.repositories.batch_repository import BatchRepository

logger = logging.getLogger("medistock.expiry_sweeper")


def sweep_near_expiry_alerts(db: Session, days: int = 30) -> List[Dict]:
    """Sweeps inventory for batches expiring within the specified days (default 30).

    Enforces business rules:
      1. Identifies near-expiry batches (expiry_date <= today + days and qty_on_hand > 0).
      2. Generates alert payloads and publishes SSE alert events to active listeners.
      3. Returns detailed summary list of generated near-expiry alert records.
    """
    cutoff_date = date.today() + timedelta(days=days)
    batch_repo = BatchRepository(db)
    expiring_batches = batch_repo.get_near_expiry_batches(cutoff_date)

    alerts_generated = []
    for batch in expiring_batches:
        days_until = (batch.expiry_date - date.today()).days
        alert_payload = {
            "event": "near_expiry_alert",
            "batch_id": batch.id,
            "product_id": batch.product_id,
            "batch_no": batch.batch_no,
            "expiry_date": str(batch.expiry_date),
            "days_until_expiry": max(0, days_until),
            "qty_on_hand": batch.qty_on_hand,
        }
        alerts_generated.append(alert_payload)
        broadcaster.publish(alert_payload)

    logger.info(f"Expiry sweeper completed: {len(alerts_generated)} near-expiry alerts refreshed.")
    return alerts_generated
