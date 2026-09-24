"""Tests for Prescriptions API (POST /api/v1/prescriptions and GET /api/v1/prescriptions/{id}).

API surface checks:
- POST /api/v1/prescriptions -> doctor role | 201 Created | 403, 422
- GET /api/v1/prescriptions/{id} -> staff role (doctor, pharmacist, manager) | 200 OK | 404
"""


def test_create_prescription_doctor_success_returns_201(client, doctor_headers, manager_headers):
    """Doctor can create a valid prescription with line items."""
    # Seed a product first
    p_res = client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={"name": "Paracetamol", "strength": "500mg"},
    )
    product_id = p_res.json()["id"]

    rx_payload = {
        "patient_name": "Jane Doe",
        "lines": [{"product_id": product_id, "qty": 14}],
    }
    response = client.post("/api/v1/prescriptions", headers=doctor_headers, json=rx_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["patient_name"] == "Jane Doe"
    assert data["status"] == "pending"
    assert len(data["lines"]) == 1
    assert data["lines"][0]["product_id"] == product_id
    assert data["lines"][0]["qty"] == 14


def test_create_prescription_pharmacist_returns_403(client, pharmacist_headers):
    """Pharmacist attempting to write a prescription receives 403 Forbidden."""
    rx_payload = {
        "patient_name": "John Smith",
        "lines": [{"product_id": 1, "qty": 10}],
    }
    response = client.post("/api/v1/prescriptions", headers=pharmacist_headers, json=rx_payload)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "403"


def test_create_prescription_nonexistent_product_returns_422(client, doctor_headers):
    """Creating a prescription referencing a non-existent product returns 422."""
    rx_payload = {
        "patient_name": "Unknown Product Test",
        "lines": [{"product_id": 999999, "qty": 5}],
    }
    response = client.post("/api/v1/prescriptions", headers=doctor_headers, json=rx_payload)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data


def test_get_prescription_by_id_staff_access_returns_200(client, doctor_headers, pharmacist_headers, manager_headers):
    """Staff members (doctor, pharmacist, manager) can view a prescription by ID."""
    p_res = client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={"name": "Amoxicillin", "strength": "250mg"},
    )
    product_id = p_res.json()["id"]

    rx_res = client.post(
        "/api/v1/prescriptions",
        headers=doctor_headers,
        json={
            "patient_name": "Alice Wonderland",
            "lines": [{"product_id": product_id, "qty": 20}],
        },
    )
    rx_id = rx_res.json()["id"]

    # Doctor lookup
    res_d = client.get(f"/api/v1/prescriptions/{rx_id}", headers=doctor_headers)
    assert res_d.status_code == 200

    # Pharmacist lookup
    res_p = client.get(f"/api/v1/prescriptions/{rx_id}", headers=pharmacist_headers)
    assert res_p.status_code == 200

    # Manager lookup
    res_m = client.get(f"/api/v1/prescriptions/{rx_id}", headers=manager_headers)
    assert res_m.status_code == 200


def test_get_prescription_unknown_id_returns_404(client, pharmacist_headers):
    """Fetching non-existent prescription returns 404 Not Found."""
    response = client.get("/api/v1/prescriptions/999999", headers=pharmacist_headers)
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "404"
