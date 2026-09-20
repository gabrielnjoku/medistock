"""Shared pytest fixtures for MediStock.

Every test runs against an isolated in-memory test database, never the dev
or prod database. We use FastAPI's dependency_overrides on `get_db` so
routers and services transparently interact with the test session.
"""

import os

# Set testing environment variables before any application imports occur
os.environ["ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-for-jwt-signing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Ensure all models are imported so SQLModel.metadata is fully populated
import app.db.base  # noqa: F401
from app.core.deps import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture(name="engine")
def engine_fixture():
    """Create a fresh in-memory SQLite engine for the test session/test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine):
    """Provide an isolated database session per test."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session):
    """Provide a TestClient with the get_db dependency overridden to use the test session."""

    def _get_test_db():
        yield session

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(name="manager_user")
def manager_user_fixture(session: Session) -> User:
    """Pre-create a manager user in the test database."""
    user = User(
        email="manager@medistock.com",
        password_hash=hash_password("ManagerPass123!"),
        role=UserRole.MANAGER,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="manager_headers")
def manager_headers_fixture(manager_user: User) -> dict[str, str]:
    """Authorization header with a valid manager JWT token."""
    token = create_access_token(subject=manager_user.email, role=manager_user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="pharmacist_user")
def pharmacist_user_fixture(session: Session) -> User:
    """Pre-create a pharmacist user in the test database."""
    user = User(
        email="pharmacist@medistock.com",
        password_hash=hash_password("PharmPass123!"),
        role=UserRole.PHARMACIST,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="pharmacist_headers")
def pharmacist_headers_fixture(pharmacist_user: User) -> dict[str, str]:
    """Authorization header with a valid pharmacist JWT token."""
    token = create_access_token(subject=pharmacist_user.email, role=pharmacist_user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="doctor_user")
def doctor_user_fixture(session: Session) -> User:
    """Pre-create a doctor user in the test database."""
    user = User(
        email="doctor@medistock.com",
        password_hash=hash_password("DoctorPass123!"),
        role=UserRole.DOCTOR,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="doctor_headers")
def doctor_headers_fixture(doctor_user: User) -> dict[str, str]:
    """Authorization header with a valid doctor JWT token."""
    token = create_access_token(subject=doctor_user.email, role=doctor_user.role.value)
    return {"Authorization": f"Bearer {token}"}
