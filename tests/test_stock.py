"""Tests for Stock API (POST /api/v1/stock/adjust and GET /api/v1/stock/movements).

API surface checks:
- POST /api/v1/stock/adjust -> pharmacist role | 201 Created | 403, 404, 422
- GET /api/v1/stock/movements -> manager role | 200 OK | 403
"""


def test_adjust_stock_pharmacist_success_returns_201(client, manager_headers, pharmacist_headers):
    """Pharmacist can adjust stock with a reason, updating quantity and creating a movement log."""
    p_res = client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={"name": "Ibuprofen", "strength": "400mg"},
    )
    product_id = p_res.json()["id"]

    b_res = client.post(
        f"/api/v1/products/{product_id}/batches",
        headers=manager_headers,
        json={"batch_no": "B_IBU_01", "expiry_date": "2027-12-31", "qty_on_hand": 50, "cost": 6.00},
    )
    batch_id = b_res.json()["id"]

    adjust_payload = {
        "batch_id": batch_id,
        "delta": -5,
        "reason": "Damaged box during count",
    }
    response = client.post("/api/v1/stock/adjust", headers=pharmacist_headers, json=adjust_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["batch_id"] == batch_id
    assert data["delta"] == -5
    assert data["reason"] == "Damaged box during count"

    # Verify inventory qty_on_hand went down to 45
    inv_res = client.get("/api/v1/inventory", headers=pharmacist_headers)
    product_inv = next(p for p in inv_res.json() if p["product_id"] == product_id)
    assert product_inv["total_qty_on_hand"] == 45


def test_adjust_stock_negative_result_returns_422(client, manager_headers, pharmacist_headers):
    """Adjustment resulting in negative stock returns 422 Unprocessable Entity."""
    p_res = client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={"name": "Diazepam", "strength": "5mg"},
    )
    product_id = p_res.json()["id"]

    b_res = client.post(
        f"/api/v1/products/{product_id}/batches",
        headers=manager_headers,
        json={"batch_no": "B_DIA_01", "expiry_date": "2027-12-31", "qty_on_hand": 10, "cost": 15.00},
    )
    batch_id = b_res.json()["id"]

    adjust_payload = {
        "batch_id": batch_id,
        "delta": -20,  # Only 10 available!
        "reason": "Excessive deduction test",
    }
    response = client.post("/api/v1/stock/adjust", headers=pharmacist_headers, json=adjust_payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "422"


def test_adjust_stock_unknown_batch_returns_404(client, pharmacist_headers):
    """Adjusting stock on non-existent batch returns 404 Not Found."""
    adjust_payload = {
        "batch_id": 999999,
        "delta": 10,
        "reason": "Ghost batch adjustment",
    }
    response = client.post("/api/v1/stock/adjust", headers=pharmacist_headers, json=adjust_payload)
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "404"


def test_adjust_stock_manager_returns_403(client, manager_headers):
    """Manager attempting pharmacist-only stock adjustment receives 403 Forbidden."""
    adjust_payload = {
        "batch_id": 1,
        "delta": 5,
        "reason": "Manager adjustment attempt",
    }
    response = client.post("/api/v1/stock/adjust", headers=manager_headers, json=adjust_payload)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "403"


def test_get_stock_movements_manager_returns_200(client, manager_headers, pharmacist_headers):
    """Manager can view stock movement audit logs."""
    p_res = client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={"name": "Metformin", "strength": "500mg"},
    )
    product_id = p_res.json()["id"]

    b_res = client.post(
        f"/api/v1/products/{product_id}/batches",
        headers=manager_headers,
        json={"batch_no": "B_MET_01", "expiry_date": "2027-12-31", "qty_on_hand": 100, "cost": 5.00},
    )
    batch_id = b_res.json()["id"]

    # Pharmacist adjusts stock
    client.post(
        "/api/v1/stock/adjust",
        headers=pharmacist_headers,
        json={"batch_id": batch_id, "delta": 10, "reason": "Restocked"},
    )

    # Manager retrieves movements log
    response = client.get("/api/v1/stock/movements", headers=manager_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(m["batch_id"] == batch_id and m["delta"] == 10 for m in data)


def test_get_stock_movements_pharmacist_returns_403(client, pharmacist_headers):
    """Pharmacist calling manager-only movements endpoint receives 403 Forbidden."""
    response = client.get("/api/v1/stock/movements", headers=pharmacist_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "403"
