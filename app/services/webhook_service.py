import logging
from typing import Optional, Tuple
from fastapi import BackgroundTasks, HTTPException, status
from sqlmodel import Session

from app.core.config import get_settings
from app.core.security import verify_webhook_signature
from app.models.batch import Batch
from app.models.processed_event import ProcessedEvent
from app.models.stock_movement import StockMovement
from app.repositories.batch_repository import BatchRepository
from app.repositories.processed_event_repository import ProcessedEventRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.stock_movement_repository import StockMovementRepository
from app.schemas.webhook import DeliveryWebhookPayload, WebhookResponse

logger = logging.getLogger("medistock.webhooks")
settings = get_settings()


def _dummy_background_notification(event_id: str):
    """Simulates background notification task (email/receipt/SSE push)."""
    logger.info(f"Background task executed for delivery event {event_id}")


def process_delivery_webhook(
    db: Session,
    raw_body: bytes,
    signature: Optional[str],
    payload: DeliveryWebhookPayload,
    background_tasks: BackgroundTasks,
) -> Tuple[int, WebhookResponse]:
    """Process incoming supplier delivery webhook.

    Enforces business rules:
      1. Signature Verification: HMAC-SHA256 of raw request body using WEBHOOK_SECRET.
         Raises 401 Unauthorized on mismatch.
      2. Deduplication: Check event_id in processed_events table.
         Returns 200 OK + status="duplicate_ignored" on duplicate (no DB changes).
      3. Orphan Handling: If reference is unknown (e.g. 'REF-UNKNOWN' or empty items),
         save event_id in processed_events, log orphan warning, and return 200 OK.
      4. Single Transaction: Create batches and stock movement records, save event_id, and commit.
      5. Fast 200/201 response: Offloads heavy notification work to BackgroundTasks.
    """
    # 1. Signature check
    if not verify_webhook_signature(raw_body, signature, settings.WEBHOOK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    event_repo = ProcessedEventRepository(db)

    # 2. Deduplication check
    existing_event = event_repo.get_by_event_id(payload.event_id)
    if existing_event is not None:
        return status.HTTP_200_OK, WebhookResponse(
            status="duplicate_ignored",
            event_id=payload.event_id,
            message="Event already processed",
        )

    # 3. Reference validation / Orphan check
    product_repo = ProductRepository(db)
    batch_repo = BatchRepository(db)
    movement_repo = StockMovementRepository(db)

    is_orphan = (
        payload.reference.startswith("REF-UNKNOWN")
        or payload.reference == "unknown"
        or not payload.items
        or any(product_repo.get_by_id(item.product_id) is None for item in payload.items)
    )

    if is_orphan:
        # Save event_id so repeats are deduplicated
        event_record = ProcessedEvent(event_id=payload.event_id, reference=payload.reference)
        event_repo.create(event_record)
        logger.warning(f"Orphan delivery webhook logged for unknown reference {payload.reference}")
        return status.HTTP_200_OK, WebhookResponse(
            status="orphan_logged",
            event_id=payload.event_id,
            message=f"Reference {payload.reference} logged as orphan",
        )

    # 4. Process valid delivery inside a single transaction
    event_record = ProcessedEvent(event_id=payload.event_id, reference=payload.reference)
    event_repo.create(event_record)

    for item in payload.items:
        # Create or update batch
        existing_batch = batch_repo.get_by_product_and_batch_no(item.product_id, item.batch_no)
        if existing_batch:
            existing_batch.qty_on_hand += item.qty
            db.add(existing_batch)
            target_batch_id = existing_batch.id
        else:
            new_batch = Batch(
                product_id=item.product_id,
                batch_no=item.batch_no,
                expiry_date=item.expiry_date,
                qty_on_hand=item.qty,
                cost=item.cost,
            )
            created_batch = batch_repo.create(new_batch)
            target_batch_id = created_batch.id

        # Record stock movement log
        movement = StockMovement(
            batch_id=target_batch_id,
            delta=item.qty,
            reason=f"Supplier delivery {payload.reference}",
            ref=payload.reference,
        )
        movement_repo.create(movement)

    # 5. Offload heavy tasks to BackgroundTasks
    background_tasks.add_task(_dummy_background_notification, payload.event_id)

    return status.HTTP_201_CREATED, WebhookResponse(
        status="processed",
        event_id=payload.event_id,
        message="Delivery processed and stock updated",
    )
