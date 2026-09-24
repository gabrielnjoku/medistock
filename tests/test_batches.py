"""Tests for MediStock Batches API (POST /api/v1/products/{id}/batches).

API surface & acceptance criteria checks:
- Given valid product and batch, when created, then 201 Created.
- Given a negative quantity, then 422.
- Given an unknown product id when creating batch, then 404.
"""


def test_add_batch_success_returns_201(client, manager_headers):
    """Manager can add a new batch to an existing product."""
    product_res = client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={"name": "Metformin", "strength": "850mg"},
    )
    product_id = product_res.json()["id"]

    batch_payload = {
        "batch_no": "B99812",
        "expiry_date": "2027-06-30",
        "qty_on_hand": 150,
        "cost": 12.50,
    }
    response = client.post(
        f"/api/v1/products/{product_id}/batches",
        headers=manager_headers,
        json=batch_payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["batch_no"] == "B99812"
    assert data["qty_on_hand"] == 150
    assert data["product_id"] == product_id


def test_add_batch_negative_quantity_returns_422(client, manager_headers):
    """Brief acceptance criterion: Given a negative quantity, then 422."""
    product_res = client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={"name": "Omeprazole", "strength": "20mg"},
    )
    product_id = product_res.json()["id"]

    batch_payload = {
        "batch_no": "B99999",
        "expiry_date": "2027-06-30",
        "qty_on_hand": -10,  # Negative quantity!
        "cost": 5.00,
    }
    response = client.post(
        f"/api/v1/products/{product_id}/batches",
        headers=manager_headers,
        json=batch_payload,
    )
    assert response.status_code == 422


def test_add_batch_unknown_product_returns_404(client, manager_headers):
    """Brief acceptance criterion: Given an unknown batch/product, then 404."""
    batch_payload = {
        "batch_no": "B12345",
        "expiry_date": "2027-06-30",
        "qty_on_hand": 50,
        "cost": 8.00,
    }
    response = client.post(
        "/api/v1/products/999999/batches",
        headers=manager_headers,
        json=batch_payload,
    )
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "404"


def test_add_batch_duplicate_batch_no_returns_409(client, manager_headers):
    """Adding a batch with identical batch_no for the same product returns 409 Conflict."""
    product_res = client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={"name": "Aspirin", "strength": "75mg"},
    )
    product_id = product_res.json()["id"]

    batch_payload = {
        "batch_no": "DUP123",
        "expiry_date": "2027-01-01",
        "qty_on_hand": 100,
        "cost": 3.50,
    }
    res1 = client.post(f"/api/v1/products/{product_id}/batches", headers=manager_headers, json=batch_payload)
    assert res1.status_code == 201

    res2 = client.post(f"/api/v1/products/{product_id}/batches", headers=manager_headers, json=batch_payload)
    assert res2.status_code == 409


def test_add_batch_pharmacist_returns_403(client, pharmacist_headers):
    """Pharmacist attempting to add batch receives 403 Forbidden."""
    batch_payload = {
        "batch_no": "B11111",
        "expiry_date": "2027-01-01",
        "qty_on_hand": 50,
        "cost": 10.00,
    }
    response = client.post("/api/v1/products/1/batches", headers=pharmacist_headers, json=batch_payload)
    assert response.status_code == 403
