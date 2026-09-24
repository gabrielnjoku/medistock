import json
import time
from datetime import date
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.broadcaster import broadcaster
from app.models.batch import Batch
from app.models.product import Product


def test_stream_unauthenticated_returns_401(client: TestClient):
    """Attempting to subscribe to the stock alerts stream without authentication must return 401."""
    response = client.get("/api/v1/stock/alerts/stream")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "401"


def test_stock_change_publishes_sse_event_within_one_second(
    client: TestClient, session: Session, pharmacist_headers: dict
):
    """Acceptance Criteria: Performing a stock change through the normal API publishes a JSON

    event to GET /api/v1/stock/alerts/stream, and the event arrives on the stream within 1 second.
    """
    # Setup test product and batch
    product = Product(name="Amoxicillin", strength="500mg")
    session.add(product)
    session.commit()
    session.refresh(product)

    batch = Batch(
        product_id=product.id,
        batch_no="BATCH-SSE-001",
        expiry_date=date(2027, 12, 31),
        qty_on_hand=50,
        cost=12.50,
    )
    session.add(batch)
    session.commit()
    session.refresh(batch)

    # Subscribe to broadcaster to simulate active SSE stream listener
    queue = broadcaster.subscribe()
    try:
        adjust_payload = {
            "batch_id": batch.id,
            "delta": 15,
            "reason": "Restock arrival",
            "ref": "REF-RESTOCK-101",
        }

        start_time = time.time()

        # Perform stock adjustment through the normal API
        response = client.post("/api/v1/stock/adjust", json=adjust_payload, headers=pharmacist_headers)
        assert response.status_code == 201

        # Assert event arrives in subscriber queue within 1 second
        raw_message = queue.get_nowait()
        elapsed = time.time() - start_time

        assert elapsed < 1.0, f"Event took {elapsed:.2f} seconds to arrive, exceeding 1s limit"

        event_payload = json.loads(raw_message)
        assert event_payload["event"] == "stock_change"
        assert event_payload["batch_id"] == batch.id
        assert event_payload["product_id"] == product.id
        assert event_payload["delta"] == 15
        assert event_payload["qty_on_hand"] == 65
        assert event_payload["reason"] == "Restock arrival"
    finally:
        broadcaster.unsubscribe(queue)


def test_stock_decrease_publishes_event_to_subscribers(
    client: TestClient, session: Session, pharmacist_headers: dict
):
    """Verifies stock reductions (e.g. dispenses/adjustments) publish updated inventory levels to subscribers."""
    product = Product(name="Paracetamol", strength="500mg")
    session.add(product)
    session.commit()
    session.refresh(product)

    batch = Batch(
        product_id=product.id,
        batch_no="BATCH-SSE-002",
        expiry_date=date(2027, 12, 31),
        qty_on_hand=100,
        cost=5.00,
    )
    session.add(batch)
    session.commit()
    session.refresh(batch)

    queue = broadcaster.subscribe()
    try:
        adjust_payload = {
            "batch_id": batch.id,
            "delta": -10,
            "reason": "Dispense adjustment",
            "ref": "REF-DISP-001",
        }
        res = client.post("/api/v1/stock/adjust", json=adjust_payload, headers=pharmacist_headers)
        assert res.status_code == 201

        raw_event = queue.get_nowait()
        data = json.loads(raw_event)
        assert data["event"] == "stock_change"
        assert data["batch_id"] == batch.id
        assert data["product_id"] == product.id
        assert data["delta"] == -10
        assert data["qty_on_hand"] == 90
        assert data["reason"] == "Dispense adjustment"
    finally:
        broadcaster.unsubscribe(queue)
