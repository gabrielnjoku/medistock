from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.firestore import get_firestore_client
from app.models.batch import Batch
from app.models.prescription import Prescription, PrescriptionLine
from app.models.product import Product
from app.models.user import User
from app.services.expiry_sweeper import sweep_near_expiry_alerts
from seed import seed_database


def test_firestore_stock_events_logged_on_adjustment_and_dispense(
    client: TestClient, session: Session, pharmacist_headers: dict[str, str], doctor_user: User
):
    """Verifies that stock movements (adjustments and dispenses) log events to Firestore."""
    firestore_client = get_firestore_client()
    initial_event_count = len(firestore_client.get_stock_events())

    # 1. Create product and batch
    product = Product(name="Amoxicillin Test", strength="250mg")
    session.add(product)
    session.commit()
    session.refresh(product)

    batch = Batch(
        product_id=product.id,
        batch_no="BAT-TEST-001",
        expiry_date=date.today() + timedelta(days=90),
        qty_on_hand=100,
        cost=3.50,
    )
    session.add(batch)
    session.commit()
    session.refresh(batch)

    # 2. Adjust stock via API
    adjust_resp = client.post(
        "/api/v1/stock/adjust",
        json={"batch_id": batch.id, "delta": 50, "reason": "Stock delivery receipt", "ref": "REF-100"},
        headers=pharmacist_headers,
    )
    assert adjust_resp.status_code == 201

    events_after_adjust = firestore_client.get_stock_events()
    assert len(events_after_adjust) > initial_event_count
    latest_event = events_after_adjust[0]
    assert latest_event["product_id"] == product.id
    assert latest_event["batch_id"] == batch.id
    assert latest_event["qty_change"] == 50
    assert latest_event["reason"] == "Stock delivery receipt"

    # 3. Create prescription and dispense
    rx = Prescription(doctor_id=doctor_user.id, patient_name="John Doe", status="pending")
    session.add(rx)
    session.commit()
    session.refresh(rx)

    rx_line = PrescriptionLine(prescription_id=rx.id, product_id=product.id, qty=30)
    session.add(rx_line)
    session.commit()

    dispense_resp = client.post(
        "/api/v1/dispenses",
        json={"prescription_id": rx.id},
        headers={**pharmacist_headers, "Idempotency-Key": "key-day10-firestore-001"},
    )
    assert dispense_resp.status_code == 201

    events_after_dispense = firestore_client.get_stock_events()
    assert len(events_after_dispense) > len(events_after_adjust)
    dispense_event = events_after_dispense[0]
    assert dispense_event["product_id"] == product.id
    assert dispense_event["qty_change"] == -30
    assert f"Dispense prescription #{rx.id}" in dispense_event["reason"]


def test_firestore_expiry_alerts_refreshed_by_sweeper(
    client: TestClient, session: Session, pharmacist_headers: dict[str, str]
):
    """Verifies that daily expiry alert sweeper refreshes Firestore expiry_alerts feed."""
    product = Product(name="Near Expiry Drug", strength="10mg")
    session.add(product)
    session.commit()
    session.refresh(product)

    near_expiry_batch = Batch(
        product_id=product.id,
        batch_no="BAT-EXPIRE-SOON",
        expiry_date=date.today() + timedelta(days=15),
        qty_on_hand=40,
        cost=10.0,
    )
    session.add(near_expiry_batch)
    session.commit()

    # Run sweeper
    sweep_near_expiry_alerts(session, days=30)

    # Query Firestore alerts endpoint
    response = client.get("/api/v1/stock/expiry-alerts", headers=pharmacist_headers)
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) >= 1
    alert_batch_nos = [a["batch_no"] for a in alerts]
    assert "BAT-EXPIRE-SOON" in alert_batch_nos


def test_seed_script_executes_successfully():
    """Verifies that the seed script initializes tables and populates data without errors."""
    seed_database()
    firestore_client = get_firestore_client()
    events = firestore_client.get_stock_events()
    alerts = firestore_client.get_expiry_alerts()
    assert len(events) >= 5
    assert len(alerts) >= 1


def test_single_error_shape_across_all_status_codes(
    client: TestClient, session: Session, pharmacist_headers: dict[str, str], doctor_headers: dict[str, str]
):
    """Verifies that 401, 403, 404, 409, 422 return exact shape {"error": {"code", "message", "request_id"}}."""

    def assert_error_shape(resp, expected_status_code: int):
        assert resp.status_code == expected_status_code
        data = resp.json()
        assert "error" in data, f"Expected 'error' key in response body: {data}"
        err = data["error"]
        assert set(err.keys()) == {"code", "message", "request_id"}
        assert str(err["code"]) == str(expected_status_code)
        assert isinstance(err["message"], str) and len(err["message"]) > 0
        assert isinstance(err["request_id"], str) and len(err["request_id"]) > 0

    # 1. 401 Unauthorized (No Token)
    r_401 = client.get("/api/v1/inventory")
    assert_error_shape(r_401, 401)

    # 2. 403 Forbidden (Doctor accessing Pharmacist endpoint)
    r_403 = client.post(
        "/api/v1/stock/adjust",
        json={"batch_id": 9999, "delta": 5, "reason": "test"},
        headers=doctor_headers,
    )
    assert_error_shape(r_403, 403)

    # 3. 404 Not Found (Non-existent batch adjustment)
    r_404 = client.post(
        "/api/v1/stock/adjust",
        json={"batch_id": 99999, "delta": 5, "reason": "test"},
        headers=pharmacist_headers,
    )
    assert_error_shape(r_404, 404)

    # 4. 422 Unprocessable Entity (Invalid payload body missing fields)
    r_422 = client.post(
        "/api/v1/stock/adjust",
        json={"invalid_key": 123},
        headers=pharmacist_headers,
    )
    assert_error_shape(r_422, 422)

    # 5. 409 Conflict (Dispense with zero/insufficient stock)
    doc_user = session.exec(select(User).where(User.email == "doctor@medistock.com")).first()
    if not doc_user:
        doc_user = User(email="doctor2@medistock.com", role="doctor", password_hash="pass")
        session.add(doc_user)
        session.commit()
        session.refresh(doc_user)

    rx_empty = Prescription(doctor_id=doc_user.id, patient_name="No Stock Patient", status="pending")
    session.add(rx_empty)
    session.commit()
    session.refresh(rx_empty)

    product_no_stock = Product(name="Empty Drug", strength="100mg")
    session.add(product_no_stock)
    session.commit()
    session.refresh(product_no_stock)

    rx_line_no_stock = PrescriptionLine(prescription_id=rx_empty.id, product_id=product_no_stock.id, qty=10)
    session.add(rx_line_no_stock)
    session.commit()

    r_409 = client.post(
        "/api/v1/dispenses",
        json={"prescription_id": rx_empty.id},
        headers={**pharmacist_headers, "Idempotency-Key": "key-day10-409-test"},
    )
    assert_error_shape(r_409, 409)
