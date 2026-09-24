from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.cache import clear_all_cache, get_cache
from app.core.rate_limiter import reset_rate_limits
from app.models.batch import Batch
from app.models.product import Product
from app.services.expiry_sweeper import sweep_near_expiry_alerts


def test_request_id_and_response_time_headers_present(client: TestClient):
    """Verifies every API response carries X-Request-ID and X-Response-Time headers."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert "x-response-time" in response.headers
    assert response.headers["x-response-time"].endswith("ms")


def test_rate_limiter_returns_429_and_retry_after_header(client: TestClient):
    """Verifies that exceeding rate limits returns 429 Too Many Requests with Retry-After header."""
    reset_rate_limits()
    payload = {"email": "invalid.user@medistock.com", "password": "WrongPassword123!"}

    # First 5 calls pass with 401
    for _ in range(5):
        res = client.post("/api/v1/auth/login", json=payload)
        assert res.status_code == 401

    # 6th call exceeds limit -> 429
    res6 = client.post("/api/v1/auth/login", json=payload)
    assert res6.status_code == 429
    assert "retry-after" in res6.headers
    assert res6.json()["error"]["code"] == "429"
    assert "rate limit" in res6.json()["error"]["message"].lower()

    reset_rate_limits()


def test_redis_hot_read_caching_and_write_invalidation(
    client: TestClient, session: Session, manager_headers: dict, pharmacist_headers: dict
):
    """Verifies GET /api/v1/inventory caches result and write operations invalidate cached keys."""
    clear_all_cache()

    product = Product(name="Azithromycin", strength="250mg")
    session.add(product)
    session.commit()

    batch = Batch(
        product_id=product.id,
        batch_no="BATCH-CACHE-001",
        expiry_date=date.today() + timedelta(days=90),
        qty_on_hand=50,
        cost=15.0,
    )
    session.add(batch)
    session.commit()

    cache_key = "cache:inventory:limit=50:offset=0:low_stock=None"

    # First GET populates cache
    resp1 = client.get("/api/v1/inventory", headers=manager_headers)
    assert resp1.status_code == 200
    cached_val = get_cache(cache_key)
    assert cached_val is not None, "Inventory hot-read failed to populate cache"

    # Stock adjustment write invalidates cache
    adjust_payload = {"batch_id": batch.id, "delta": 10, "reason": "Restock", "ref": "REF-CACHE-001"}
    resp_adj = client.post("/api/v1/stock/adjust", json=adjust_payload, headers=pharmacist_headers)
    assert resp_adj.status_code == 201

    # Assert cache key was invalidated
    invalidated_val = get_cache(cache_key)
    assert invalidated_val is None, "Stock write failed to invalidate inventory cache key"

    clear_all_cache()


def test_expiry_sweeper_identifies_near_expiry_batches(session: Session):
    """Verifies the daily near-expiry sweeper job identifies expiring batches."""
    product = Product(name="Cefuroxime", strength="500mg")
    session.add(product)
    session.commit()

    # Batch expiring in 15 days
    expiring_batch = Batch(
        product_id=product.id,
        batch_no="BATCH-SWEEP-001",
        expiry_date=date.today() + timedelta(days=15),
        qty_on_hand=30,
        cost=18.0,
    )
    session.add(expiring_batch)
    session.commit()

    alerts = sweep_near_expiry_alerts(session, days=30)
    assert len(alerts) >= 1

    matching = [a for a in alerts if a["batch_no"] == "BATCH-SWEEP-001"]
    assert len(matching) == 1
    assert matching[0]["days_until_expiry"] == 15
    assert matching[0]["qty_on_hand"] == 30
