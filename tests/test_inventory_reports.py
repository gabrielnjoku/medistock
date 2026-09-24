"""Tests for Inventory listing (GET /api/v1/inventory) and Reports (GET /api/v1/reports/*).

API surface checks:
- GET /api/v1/inventory -> staff role (manager, pharmacist, doctor) | 200 OK | 401
- GET /api/v1/reports/low-stock -> manager role | 200 OK | 403
- GET /api/v1/reports/near-expiry -> manager role | 200 OK | 403
"""

from datetime import date, timedelta


def test_get_inventory_staff_access_returns_200(client, manager_headers, pharmacist_headers, doctor_headers):
    """All staff roles (manager, pharmacist, doctor) can access the inventory list."""
    # Manager access
    res_m = client.get("/api/v1/inventory", headers=manager_headers)
    assert res_m.status_code == 200

    # Pharmacist access
    res_p = client.get("/api/v1/inventory", headers=pharmacist_headers)
    assert res_p.status_code == 200

    # Doctor access
    res_d = client.get("/api/v1/inventory", headers=doctor_headers)
    assert res_d.status_code == 200


def test_get_inventory_unauthorized_returns_401(client):
    """Unauthenticated call to GET /api/v1/inventory returns 401."""
    response = client.get("/api/v1/inventory")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "401"


def test_low_stock_report_manager_returns_200(client, manager_headers):
    """Manager can fetch the low-stock report."""
    # Seed a product with low stock (5 units)
    p_res = client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={"name": "Loratadine", "strength": "10mg"},
    )
    product_id = p_res.json()["id"]
    client.post(
        f"/api/v1/products/{product_id}/batches",
        headers=manager_headers,
        json={
            "batch_no": "LOW100",
            "expiry_date": "2028-01-01",
            "qty_on_hand": 5,
            "cost": 4.00,
        },
    )

    response = client.get("/api/v1/reports/low-stock", headers=manager_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["product_id"] == product_id for item in data)


def test_low_stock_report_pharmacist_returns_403(client, pharmacist_headers):
    """Pharmacist calling manager-only report endpoint receives 403 Forbidden."""
    response = client.get("/api/v1/reports/low-stock", headers=pharmacist_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "403"


def test_near_expiry_report_manager_returns_200(client, manager_headers):
    """Manager can fetch near-expiry report."""
    p_res = client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={"name": "Insulin", "strength": "100IU/ml"},
    )
    product_id = p_res.json()["id"]

    near_date = (date.today() + timedelta(days=15)).isoformat()
    client.post(
        f"/api/v1/products/{product_id}/batches",
        headers=manager_headers,
        json={
            "batch_no": "EXPIRING_SOON",
            "expiry_date": near_date,
            "qty_on_hand": 20,
            "cost": 50.00,
        },
    )

    response = client.get("/api/v1/reports/near-expiry?days=30", headers=manager_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["batch_no"] == "EXPIRING_SOON" for item in data)


def test_near_expiry_report_pharmacist_returns_403(client, pharmacist_headers):
    """Pharmacist calling near-expiry report endpoint receives 403 Forbidden."""
    response = client.get("/api/v1/reports/near-expiry", headers=pharmacist_headers)
    assert response.status_code == 403
