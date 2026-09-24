"""Acceptance criteria tests for MediStock Authentication & RBAC.

Acceptance criteria from the project brief:
- Given no token -> 401
- Given a pharmacist token on a manager route -> 403
- Given valid manager token on manager route -> 201
- Given duplicate email on register -> 409
- Given valid credentials on login -> 200 with JWT access token
- Given invalid credentials on login -> 401
"""

from app.models.user import User


def test_register_without_token_returns_401(client):
    """Calling manager-only register route with no authorization header returns 401."""
    payload = {
        "email": "nurse@medistock.com",
        "password": "SecurePassword123!",
        "role": "pharmacist",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "401"
    assert "request_id" in data["error"]


def test_register_with_pharmacist_token_returns_403(client, pharmacist_headers):
    """Brief acceptance criterion: Given a pharmacist token on a manager route -> 403."""
    payload = {
        "email": "assistant@medistock.com",
        "password": "SecurePassword123!",
        "role": "pharmacist",
    }
    response = client.post("/api/v1/auth/register", headers=pharmacist_headers, json=payload)
    assert response.status_code == 403
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "403"
    assert "request_id" in data["error"]


def test_register_with_doctor_token_returns_403(client, doctor_headers):
    """A doctor attempting to register staff accounts must receive 403."""
    payload = {
        "email": "assistant@medistock.com",
        "password": "SecurePassword123!",
        "role": "doctor",
    }
    response = client.post("/api/v1/auth/register", headers=doctor_headers, json=payload)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "403"


def test_register_with_manager_token_returns_201_and_never_leaks_password_hash(client, manager_headers):
    """A manager can register a new user; response model never leaks password_hash."""
    payload = {
        "email": "staff.kemi@medistock.com",
        "password": "SecurePassword123!",
        "role": "pharmacist",
    }
    response = client.post("/api/v1/auth/register", headers=manager_headers, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "staff.kemi@medistock.com"
    assert data["role"] == "pharmacist"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email_returns_409(client, manager_headers, pharmacist_user: User):
    """Registering an email that already exists must return 409 Conflict."""
    payload = {
        "email": pharmacist_user.email,
        "password": "NewPassword123!",
        "role": "pharmacist",
    }
    response = client.post("/api/v1/auth/register", headers=manager_headers, json=payload)
    assert response.status_code == 409
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "409"
    assert "already registered" in data["error"]["message"].lower()


def test_login_with_valid_credentials_returns_token(client, manager_user: User):
    """Valid credentials return 200 with a bearer JWT token."""
    login_payload = {
        "email": manager_user.email,
        "password": "ManagerPass123!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_with_wrong_password_returns_401(client, manager_user: User):
    """Login with wrong password fails with 401."""
    login_payload = {
        "email": manager_user.email,
        "password": "IncorrectPassword999!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "401"


def test_login_with_nonexistent_email_returns_401(client):
    """Login with unknown email fails with 401."""
    login_payload = {
        "email": "ghost@medistock.com",
        "password": "SomePassword123!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "401"


def test_request_with_invalid_token_returns_401(client):
    """Calling protected endpoint with malformed/forged token returns 401."""
    headers = {"Authorization": "Bearer completely-bogus-token-data"}
    payload = {
        "email": "somebody@medistock.com",
        "password": "SecurePassword123!",
        "role": "doctor",
    }
    response = client.post("/api/v1/auth/register", headers=headers, json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "401"
