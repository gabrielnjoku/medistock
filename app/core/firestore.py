import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FirestoreMemoryClient:
    """In-memory fallback client used during tests or local development
    when live GCP Firestore credentials / emulator are not configured.
    """

    def __init__(self) -> None:
        self.stock_events: List[Dict[str, Any]] = []
        self.expiry_alerts: Dict[str, Dict[str, Any]] = {}

    def log_stock_event(
        self,
        product_id: int,
        batch_id: int,
        qty_change: int,
        reason: str,
        performed_by: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        event_id = str(uuid.uuid4())
        event_data = {
            "event_id": event_id,
            "product_id": product_id,
            "batch_id": batch_id,
            "qty_change": qty_change,
            "reason": reason,
            "performed_by": performed_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        self.stock_events.append(event_data)
        logger.info(f"[Firestore:Memory] Logged stock event {event_id} for product {product_id}, batch {batch_id}")
        return event_data

    def refresh_expiry_alerts(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.expiry_alerts.clear()
        refreshed: List[Dict[str, Any]] = []
        for alert in alerts:
            alert_id = f"batch_{alert['batch_id']}"
            alert_doc = {
                "alert_id": alert_id,
                "batch_id": alert["batch_id"],
                "batch_no": alert["batch_no"],
                "product_id": alert["product_id"],
                "product_name": alert.get("product_name", ""),
                "expiry_date": str(alert["expiry_date"]),
                "days_until_expiry": alert["days_until_expiry"],
                "qty_on_hand": alert["qty_on_hand"],
                "status": alert.get("status", "NEAR_EXPIRY"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.expiry_alerts[alert_id] = alert_doc
            refreshed.append(alert_doc)
        logger.info(f"[Firestore:Memory] Refreshed {len(refreshed)} expiry alert docs")
        return refreshed

    def get_stock_events(self, product_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        events = self.stock_events
        if product_id is not None:
            events = [e for e in events if e["product_id"] == product_id]
        sorted_events = sorted(events, key=lambda x: x["timestamp"], reverse=True)
        return sorted_events[:limit]

    def get_expiry_alerts(self) -> List[Dict[str, Any]]:
        return list(self.expiry_alerts.values())


class FirestoreClientWrapper:
    """Wrapper managing connection to Google Cloud Firestore (or emulator),
    falling back seamlessly to FirestoreMemoryClient when offline.
    """

    def __init__(self) -> None:
        self._db: Any = None
        self._memory_client = FirestoreMemoryClient()
        self._init_client()

    def _init_client(self) -> None:
        settings = get_settings()
        try:
            from google.cloud import firestore  # type: ignore

            project_id = os.getenv("FIRESTORE_PROJECT_ID", settings.FIRESTORE_PROJECT_ID)
            self._db = firestore.Client(project=project_id)
            logger.info(f"[Firestore] Connected to GCP Firestore project '{project_id}'")
        except Exception as exc:
            logger.info(f"[Firestore] GCP Firestore client not initialized ({exc}). Using in-memory fallback.")
            self._db = None

    def log_stock_event(
        self,
        product_id: int,
        batch_id: int,
        qty_change: int,
        reason: str,
        performed_by: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if self._db is not None:
            try:
                event_id = str(uuid.uuid4())
                event_data = {
                    "event_id": event_id,
                    "product_id": product_id,
                    "batch_id": batch_id,
                    "qty_change": qty_change,
                    "reason": reason,
                    "performed_by": performed_by,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": metadata or {},
                }
                self._db.collection("stock_events").document(event_id).set(event_data)
                logger.info(f"[Firestore] Logged event {event_id} for product {product_id}")
                return event_data
            except Exception as exc:
                logger.warning(f"[Firestore] Failed to log event to GCP Firestore ({exc}). Using fallback.")
        return self._memory_client.log_stock_event(
            product_id=product_id,
            batch_id=batch_id,
            qty_change=qty_change,
            reason=reason,
            performed_by=performed_by,
            metadata=metadata,
        )

    def refresh_expiry_alerts(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self._db is not None:
            try:
                batch_writer = self._db.batch()
                refreshed: List[Dict[str, Any]] = []

                # Clear old docs in expiry_alerts collection
                docs = self._db.collection("expiry_alerts").stream()
                for doc in docs:
                    batch_writer.delete(doc.reference)

                for alert in alerts:
                    alert_id = f"batch_{alert['batch_id']}"
                    alert_doc = {
                        "alert_id": alert_id,
                        "batch_id": alert["batch_id"],
                        "batch_no": alert["batch_no"],
                        "product_id": alert["product_id"],
                        "product_name": alert.get("product_name", ""),
                        "expiry_date": str(alert["expiry_date"]),
                        "days_until_expiry": alert["days_until_expiry"],
                        "qty_on_hand": alert["qty_on_hand"],
                        "status": alert.get("status", "NEAR_EXPIRY"),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    doc_ref = self._db.collection("expiry_alerts").document(alert_id)
                    batch_writer.set(doc_ref, alert_doc)
                    refreshed.append(alert_doc)

                batch_writer.commit()
                logger.info(f"[Firestore] Refreshed {len(refreshed)} expiry alerts in Firestore")
                return refreshed
            except Exception as exc:
                logger.warning(f"[Firestore] Failed to refresh GCP Firestore alerts ({exc}). Using fallback.")

        return self._memory_client.refresh_expiry_alerts(alerts)

    def get_stock_events(self, product_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if self._db is not None:
            try:
                query = self._db.collection("stock_events")
                if product_id is not None:
                    query = query.where("product_id", "==", product_id)
                query = query.order_by("timestamp", direction="DESCENDING").limit(limit)
                docs = query.stream()
                return [d.to_dict() for d in docs]
            except Exception as exc:
                logger.warning(f"[Firestore] Failed to fetch GCP Firestore events ({exc}). Using fallback.")

        return self._memory_client.get_stock_events(product_id=product_id, limit=limit)

    def get_expiry_alerts(self) -> List[Dict[str, Any]]:
        if self._db is not None:
            try:
                docs = self._db.collection("expiry_alerts").stream()
                return [d.to_dict() for d in docs]
            except Exception as exc:
                logger.warning(f"[Firestore] Failed to fetch GCP Firestore alerts ({exc}). Using fallback.")

        return self._memory_client.get_expiry_alerts()


_firestore_wrapper = FirestoreClientWrapper()


def get_firestore_client() -> FirestoreClientWrapper:
    return _firestore_wrapper
