"""Tests for Supplier Delivery Webhook API (POST /api/v1/webhooks/deliveries).

Acceptance criteria from the brief:
- Valid delivery webhook -> 201 Created and batches/stock are created.
- Duplicate delivery id -> 200 OK and no duplicate batches/changes.
- Bad signature -> 401 Unauthorized.
- Unknown reference -> 200 OK and logged as an orphan.
"""

import json

from app.core.config import get_settings
from app.core.security import compute_webhook_signature

settings = get_settings()


def test_valid_delivery_webhook_creates_batches_returns_201(client, manager_headers):
    """Given a signed delivery webhook, returns 201 and creates batches/stock."""
    # Seed a product first
    p_res = client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={"name": "Cefuroxime", "strength": "500mg"},
    )
    product_id = p_res.json()["id"]

    payload = {
        "event_id": "evt_del_001",
        "type": "delivery.dispatched",
        "reference": "PO-DEL-101",
        "items": [
            {
                "product_id": product_id,
                "batch_no": "B_CEF_001",
                "expiry_date": "2028-06-30",
                "qty": 300,
                "cost": 18.00,
            }
        ],
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = compute_webhook_signature(raw_body, settings.WEBHOOK_SECRET)
    headers = {"X-Signature": f"sha256={sig}", "Content-Type": "application/json"}

    response = client.post("/api/v1/webhooks/deliveries", content=raw_body, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "processed"
    assert data["event_id"] == "evt_del_001"

    # Verify inventory was updated with 300 items
    inv_res = client.get("/api/v1/inventory", headers=manager_headers)
    prod = next(p for p in inv_res.json() if p["product_id"] == product_id)
    assert prod["total_qty_on_hand"] == 300


def test_duplicate_delivery_webhook_returns_200_no_duplicate_batches(client, manager_headers):
    """Given the same delivery id again, returns 200 OK and no duplicate batches."""
    p_res = client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={"name": "Azithromycin", "strength": "500mg"},
    )
    product_id = p_res.json()["id"]

    payload = {
        "event_id": "evt_del_REPEAT",
        "type": "delivery.dispatched",
        "reference": "PO-DEL-102",
        "items": [
            {
                "product_id": product_id,
                "batch_no": "B_AZI_99",
                "expiry_date": "2028-12-31",
                "qty": 100,
                "cost": 22.00,
            }
        ],
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = compute_webhook_signature(raw_body, settings.WEBHOOK_SECRET)
    headers = {"X-Signature": sig, "Content-Type": "application/json"}

    # First call -> 201 Created
    res1 = client.post("/api/v1/webhooks/deliveries", content=raw_body, headers=headers)
    assert res1.status_code == 201

    # Second call with same event_id -> 200 OK (duplicate ignored)
    res2 = client.post("/api/v1/webhooks/deliveries", content=raw_body, headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "duplicate_ignored"
    assert data2["event_id"] == "evt_del_REPEAT"

    # Total inventory should still be 100, not 200
    inv_res = client.get("/api/v1/inventory", headers=manager_headers)
    prod = next(p for p in inv_res.json() if p["product_id"] == product_id)
    assert prod["total_qty_on_hand"] == 100


def test_bad_signature_webhook_returns_401(client):
    """Given a bad signature or missing X-Signature header, returns 401 Unauthorized."""
    payload = {
        "event_id": "evt_del_BAD_SIG",
        "type": "delivery.dispatched",
        "reference": "PO-DEL-103",
        "items": [],
    }
    raw_body = json.dumps(payload).encode("utf-8")
    headers = {"X-Signature": "invalid_signature_hash_value", "Content-Type": "application/json"}

    response = client.post("/api/v1/webhooks/deliveries", content=raw_body, headers=headers)
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "401"


def test_unknown_reference_webhook_returns_200_logged_as_orphan(client):
    """Given an unknown reference, returns 200 OK and logs as an orphan."""
    payload = {
        "event_id": "evt_del_ORPHAN",
        "type": "delivery.dispatched",
        "reference": "REF-UNKNOWN-99999",
        "items": [],
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = compute_webhook_signature(raw_body, settings.WEBHOOK_SECRET)
    headers = {"X-Signature": sig, "Content-Type": "application/json"}

    response = client.post("/api/v1/webhooks/deliveries", content=raw_body, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "orphan_logged"
    assert data["event_id"] == "evt_del_ORPHAN"
