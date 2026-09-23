import hashlib
import json
from datetime import date, datetime, timezone
from typing import List
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.broadcaster import broadcaster
from app.models.dispense import Dispense, DispenseLine
from app.models.idempotency_key import IdempotencyKey
from app.models.stock_movement import StockMovement
from app.repositories.batch_repository import BatchRepository
from app.repositories.dispense_repository import DispenseRepository
from app.repositories.idempotency_repository import IdempotencyRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.repositories.stock_movement_repository import StockMovementRepository
from app.schemas.dispense import DispenseCreate, DispenseLineRead, DispenseRead


def compute_request_hash(path: str, payload_dict: dict) -> str:
    """Computes a SHA-256 fingerprint of the request path and JSON body payload."""
    raw = f"{path}:{json.dumps(payload_dict, sort_keys=True)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def dispense_prescription(
    db: Session,
    idempotency_key: str,
    path: str,
    pharmacist_id: int,
    payload: DispenseCreate,
) -> DispenseRead:
    """Fulfills a pending prescription with atomic transaction semantics.

    Enforces business rules:
      1. Idempotency Check:
         - Missing key -> 422 Unprocessable Entity.
         - Existing key + matching request_hash -> return saved response payload (201).
         - Existing key + different request_hash -> raise 422 Unprocessable Entity.
      2. Prescription Check:
         - Must exist and status == "pending" (raises 404/422).
      3. Row Locking & FEFO Stock Deduction:
         - Query non-expired batches (expiry_date >= date.today()) ordered by expiry_date ASC, id ASC.
         - Apply SELECT ... FOR UPDATE row-level locking.
         - If available non-expired stock < required qty -> raise 409 Conflict (transaction rolls back).
         - Deduct qty across candidate batches in FEFO order.
         - Log StockMovement per batch and publish SSE alert.
      4. Persist Dispense, DispenseLine, update prescription status to "dispensed".
      5. Cache IdempotencyKey record and commit single transaction.
    """
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency-Key header is required for dispense operations",
        )

    req_hash = compute_request_hash(path, payload.model_dump())
    idem_repo = IdempotencyRepository(db)

    # 1. Check idempotency key record
    existing_key = idem_repo.get_by_key(idempotency_key)
    if existing_key is not None:
        if existing_key.request_hash == req_hash:
            # Replay saved response without executing business logic or touching DB stock
            saved_data = json.loads(existing_key.response_body)
            return DispenseRead.model_validate(saved_data)
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Idempotency-Key reused with different request payload",
            )

    # 2. Check prescription existence & status
    rx_repo = PrescriptionRepository(db)
    rx = rx_repo.get_by_id(payload.prescription_id)
    if rx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription with id {payload.prescription_id} not found",
        )
    if rx.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Prescription {payload.prescription_id} is already {rx.status}",
        )

    rx_lines = rx_repo.get_lines(rx.id)
    if not rx_lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Prescription {payload.prescription_id} has no line items",
        )

    batch_repo = BatchRepository(db)
    movement_repo = StockMovementRepository(db)
    today = date.today()

    dispense_lines_to_create: List[DispenseLine] = []
    events_to_publish: List[dict] = []

    # Create Dispense header
    dispense = Dispense(
        prescription_id=rx.id,
        pharmacist_id=pharmacist_id,
        dispensed_at=datetime.now(timezone.utc),
    )
    db.add(dispense)
    db.flush()
    db.refresh(dispense)

    # 3. Process each prescription line with FEFO row-locking
    for rx_line in rx_lines:
        needed_qty = rx_line.qty

        # Lock and retrieve candidate non-expired batches ordered by expiry_date ASC, id ASC
        candidate_batches = batch_repo.get_available_fefo_batches_with_lock(
            product_id=rx_line.product_id, current_date=today
        )

        total_avail = sum(b.qty_on_hand for b in candidate_batches)
        if total_avail < needed_qty:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient non-expired stock for product_id {rx_line.product_id}: requested {needed_qty}, available {total_avail}",
            )

        remaining_needed = needed_qty
        for b in candidate_batches:
            if remaining_needed <= 0:
                break

            deduct_qty = min(b.qty_on_hand, remaining_needed)
            b.qty_on_hand -= deduct_qty
            remaining_needed -= deduct_qty
            db.add(b)

            dispense_lines_to_create.append(
                DispenseLine(
                    dispense_id=dispense.id,
                    batch_id=b.id,
                    product_id=rx_line.product_id,
                    qty=deduct_qty,
                )
            )

            # Audit stock movement
            movement = StockMovement(
                batch_id=b.id,
                delta=-deduct_qty,
                reason=f"Dispense prescription #{rx.id}",
                ref=f"DISP-{dispense.id}",
            )
            movement_repo.create(movement)

            events_to_publish.append({
                "event": "stock_change",
                "batch_id": b.id,
                "product_id": rx_line.product_id,
                "delta": -deduct_qty,
                "qty_on_hand": b.qty_on_hand,
                "reason": f"Dispense prescription #{rx.id}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    # Save dispense lines & update prescription status
    dispense_repo = DispenseRepository(db)
    dispense_repo.create(dispense, dispense_lines_to_create)

    rx.status = "dispensed"
    db.add(rx)

    # Build response model
    saved_lines = dispense_repo.get_lines(dispense.id)
    line_reads = [DispenseLineRead.model_validate(l) for l in saved_lines]
    dispense_read = DispenseRead(
        id=dispense.id,
        prescription_id=dispense.prescription_id,
        pharmacist_id=dispense.pharmacist_id,
        dispensed_at=dispense.dispensed_at,
        lines=line_reads,
    )

    # 4. Cache idempotency key record inside the single transaction
    idem_record = IdempotencyKey(
        key=idempotency_key,
        request_hash=req_hash,
        response_code=status.HTTP_201_CREATED,
        response_body=dispense_read.model_dump_json(),
    )
    idem_repo.create(idem_record)

    # 5. Commit atomic transaction
    db.commit()
    db.refresh(dispense)

    # 6. Publish SSE notifications to stream subscribers
    for event in events_to_publish:
        broadcaster.publish(event)

    return dispense_read
