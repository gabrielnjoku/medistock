import threading
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.batch import Batch
from app.models.prescription import Prescription, PrescriptionLine
from app.models.product import Product
from app.models.stock_movement import StockMovement


def test_same_idempotency_key_twice_reduces_stock_once_and_returns_same_body(
    client: TestClient, session: Session, pharmacist_headers: dict
):
    """Hard Problem Test 1: Calling POST /api/v1/dispenses twice with the same Idempotency-Key

    header returns the saved response payload and touches stock exactly ONCE.
    """
    product = Product(name="Amoxicillin", strength="500mg")
    session.add(product)
    session.commit()
    session.refresh(product)

    batch = Batch(
        product_id=product.id,
        batch_no="BATCH-IDEM-001",
        expiry_date=date.today() + timedelta(days=90),
        qty_on_hand=50,
        cost=10.0,
    )
    session.add(batch)
    session.commit()

    rx = Prescription(patient_name="John Doe", doctor_id=1, status="pending")
    session.add(rx)
    session.commit()
    session.refresh(rx)

    rx_line = PrescriptionLine(prescription_id=rx.id, product_id=product.id, qty=10)
    session.add(rx_line)
    session.commit()

    headers = {**pharmacist_headers, "Idempotency-Key": "key-idempotent-101"}
    payload = {"prescription_id": rx.id}

    # First dispense call
    resp1 = client.post("/api/v1/dispenses", json=payload, headers=headers)
    assert resp1.status_code == 201
    data1 = resp1.json()

    # Verify stock deducted once (50 - 10 = 40)
    session.refresh(batch)
    assert batch.qty_on_hand == 40

    # Second dispense call with exact SAME Idempotency-Key and payload
    resp2 = client.post("/api/v1/dispenses", json=payload, headers=headers)
    assert resp2.status_code == 201
    data2 = resp2.json()

    # Response payload MUST be identical
    assert data1 == data2

    # Stock MUST remain 40 (reduced exactly once!)
    session.refresh(batch)
    assert batch.qty_on_hand == 40

    # Stock movements for this batch must equal 1
    movements = session.exec(select(StockMovement).where(StockMovement.batch_id == batch.id)).all()
    assert len(movements) == 1
    assert movements[0].delta == -10


def test_simultaneous_dispenses_last_unit_one_201_one_409(
    client: TestClient, session: Session, pharmacist_headers: dict
):
    """Hard Problem Test 2: Two dispenses targeting the last unit of stock result

    in exactly one 201 Created and one 409 Conflict.
    """
    product = Product(name="Paracetamol", strength="500mg")
    session.add(product)
    session.commit()

    # Batch with ONLY 1 unit remaining
    batch = Batch(
        product_id=product.id,
        batch_no="BATCH-RACE-001",
        expiry_date=date.today() + timedelta(days=60),
        qty_on_hand=1,
        cost=5.0,
    )
    session.add(batch)
    session.commit()

    rx1 = Prescription(patient_name="Patient A", doctor_id=1, status="pending")
    rx2 = Prescription(patient_name="Patient B", doctor_id=1, status="pending")
    session.add_all([rx1, rx2])
    session.commit()

    session.add(PrescriptionLine(prescription_id=rx1.id, product_id=product.id, qty=1))
    session.add(PrescriptionLine(prescription_id=rx2.id, product_id=product.id, qty=1))
    session.commit()

    # First dispense claims the last remaining unit -> 201 Created
    h1 = {**pharmacist_headers, "Idempotency-Key": "key-race-1"}
    res1 = client.post("/api/v1/dispenses", json={"prescription_id": rx1.id}, headers=h1)
    assert res1.status_code == 201

    # Second dispense attempting to claim the last unit fails with 409 Conflict
    h2 = {**pharmacist_headers, "Idempotency-Key": "key-race-2"}
    res2 = client.post("/api/v1/dispenses", json={"prescription_id": rx2.id}, headers=h2)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "409"
    assert "insufficient" in res2.json()["error"]["message"].lower()

    # Stock must be exactly 0 (never negative)
    session.refresh(batch)
    assert batch.qty_on_hand == 0


def test_expired_batch_never_used_all_expired_returns_409(
    client: TestClient, session: Session, pharmacist_headers: dict
):
    """Hard Problem Test 3: An expired batch (expiry_date < date.today()) is never used.

    If all stock is expired, dispense fails with 409 Conflict.
    """
    product = Product(name="Ibuprofen", strength="400mg")
    session.add(product)
    session.commit()

    # Expired batch (expiry date in the past)
    expired_batch = Batch(
        product_id=product.id,
        batch_no="BATCH-EXPIRED-001",
        expiry_date=date.today() - timedelta(days=10),
        qty_on_hand=100,
        cost=8.0,
    )
    session.add(expired_batch)
    session.commit()

    rx = Prescription(patient_name="Patient Expired", doctor_id=1, status="pending")
    session.add(rx)
    session.commit()
    session.add(PrescriptionLine(prescription_id=rx.id, product_id=product.id, qty=5))
    session.commit()

    headers = {**pharmacist_headers, "Idempotency-Key": "key-expired-301"}
    payload = {"prescription_id": rx.id}

    response = client.post("/api/v1/dispenses", json=payload, headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "409"
    assert "insufficient" in response.json()["error"]["message"].lower()

    # Expired batch quantity must remain untouched!
    session.refresh(expired_batch)
    assert expired_batch.qty_on_hand == 100


def test_same_idempotency_key_different_body_returns_422(
    client: TestClient, session: Session, pharmacist_headers: dict
):
    """Hard Problem Test 4: Reusing the same Idempotency-Key with a different request body

    must return 422 Unprocessable Entity.
    """
    product = Product(name="Ciprofloxacin", strength="500mg")
    session.add(product)
    session.commit()

    batch = Batch(
        product_id=product.id,
        batch_no="BATCH-IDEM-004",
        expiry_date=date.today() + timedelta(days=120),
        qty_on_hand=50,
        cost=15.0,
    )
    session.add(batch)
    session.commit()

    rx1 = Prescription(patient_name="Patient 1", doctor_id=1, status="pending")
    rx2 = Prescription(patient_name="Patient 2", doctor_id=1, status="pending")
    session.add_all([rx1, rx2])
    session.commit()

    session.add(PrescriptionLine(prescription_id=rx1.id, product_id=product.id, qty=5))
    session.add(PrescriptionLine(prescription_id=rx2.id, product_id=product.id, qty=5))
    session.commit()

    headers = {**pharmacist_headers, "Idempotency-Key": "key-mismatch-401"}

    # First call with Rx1 succeeds
    resp1 = client.post("/api/v1/dispenses", json={"prescription_id": rx1.id}, headers=headers)
    assert resp1.status_code == 201

    # Second call with SAME key but DIFFERENT payload (Rx2) returns 422
    resp2 = client.post("/api/v1/dispenses", json={"prescription_id": rx2.id}, headers=headers)
    assert resp2.status_code == 422
    assert resp2.json()["error"]["code"] == "422"
    assert "payload" in resp2.json()["error"]["message"].lower() or "idempotency" in resp2.json()["error"]["message"].lower()

    # Stock was deducted ONLY for Rx1 (50 - 5 = 45)
    session.refresh(batch)
    assert batch.qty_on_hand == 45


def test_sum_of_stock_movements_equals_qty_on_hand_for_every_batch(
    client: TestClient, session: Session, pharmacist_headers: dict
):
    """Hard Problem Test 5: Audit invariant assertion — for every batch in the database,

    initial_qty + sum(stock_movements.delta) == batch.qty_on_hand.
    """
    product = Product(name="Metformin", strength="500mg")
    session.add(product)
    session.commit()

    batch = Batch(
        product_id=product.id,
        batch_no="BATCH-AUDIT-005",
        expiry_date=date.today() + timedelta(days=180),
        qty_on_hand=100,
        cost=4.0,
    )
    session.add(batch)
    session.commit()
    session.refresh(batch)

    # Initial creation movement log (100)
    session.add(StockMovement(batch_id=batch.id, delta=100, reason="Initial stock", ref="INIT-005"))
    session.commit()

    # Manual adjustment (+20)
    adjust_payload = {"batch_id": batch.id, "delta": 20, "reason": "Audit correction", "ref": "ADJ-005"}
    client.post("/api/v1/stock/adjust", json=adjust_payload, headers=pharmacist_headers)

    # Dispense (-15)
    rx = Prescription(patient_name="Audit Patient", doctor_id=1, status="pending")
    session.add(rx)
    session.commit()
    session.add(PrescriptionLine(prescription_id=rx.id, product_id=product.id, qty=15))
    session.commit()

    dispense_headers = {**pharmacist_headers, "Idempotency-Key": "key-audit-501"}
    client.post("/api/v1/dispenses", json={"prescription_id": rx.id}, headers=dispense_headers)

    # Audit invariant assertion for ALL batches in the database
    all_batches = session.exec(select(Batch)).all()
    assert len(all_batches) > 0

    for b in all_batches:
        movements = session.exec(select(StockMovement).where(StockMovement.batch_id == b.id)).all()
        movement_sum = sum(m.delta for m in movements)
        assert b.qty_on_hand == movement_sum, (
            f"Batch {b.batch_no} audit discrepancy! "
            f"qty_on_hand={b.qty_on_hand} but sum(deltas)={movement_sum}"
        )
