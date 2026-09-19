"""Shared pytest fixtures.

TODO before Day 3-4's tests-first hard-problem suite: point this at a
separate test database, never the dev DB — e.g. a DATABASE_URL_TEST
env var plus a fixture that creates and drops tables per test session
or per test, so tests never depend on (or corrupt) each other's data.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)
