"""Tests for MediStock Products API (POST /api/v1/products).

API surface checks:
- POST /api/v1/products (manager role | 201 Created | 401, 403, 409, 422)
"""


def test_create_product_success_returns_201(client, manager_headers):
    """Manager can create a new product with valid name and strength."""
    payload = {"name": "Amoxicillin", "strength": "500mg"}
    response = client.post("/api/v1/products", headers=manager_headers, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Amoxicillin"
    assert data["strength"] == "500mg"
    assert "id" in data


def test_create_product_duplicate_returns_409(client, manager_headers):
    """Creating a product with duplicate (name, strength) returns 409 Conflict."""
    payload = {"name": "Paracetamol", "strength": "500mg"}
    response1 = client.post("/api/v1/products", headers=manager_headers, json=payload)
    assert response1.status_code == 201

    response2 = client.post("/api/v1/products", headers=manager_headers, json=payload)
    assert response2.status_code == 409
    data = response2.json()
    assert "error" in data
    assert data["error"]["code"] == "409"


def test_create_product_without_token_returns_401(client):
    """Calling POST /api/v1/products with no token returns 401 Unauthorized."""
    payload = {"name": "Ibuprofen", "strength": "200mg"}
    response = client.post("/api/v1/products", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "401"


def test_create_product_pharmacist_returns_403(client, pharmacist_headers):
    """Pharmacist calling manager-only product endpoint receives 403 Forbidden."""
    payload = {"name": "Ciprofloxacin", "strength": "500mg"}
    response = client.post("/api/v1/products", headers=pharmacist_headers, json=payload)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "403"


def test_create_product_invalid_body_returns_422(client, manager_headers):
    """Empty payload or invalid fields return 422 Unprocessable Entity."""
    payload = {"name": "", "strength": ""}
    response = client.post("/api/v1/products", headers=manager_headers, json=payload)
    assert response.status_code == 422
