import json
from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.cache import get_cache, set_cache
from app.core.deps import get_db, require_role
from app.models.user import User, UserRole
from app.schemas.report import LowStockReportItem, NearExpiryReportItem
from app.services import report_service

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get(
    "/low-stock",
    response_model=List[LowStockReportItem],
    status_code=status.HTTP_200_OK,
    summary="Get low-stock report",
    description="Manager-only per brief. Returns products with stock level below or equal to threshold (default 10).",
    responses={
        401: {"description": "Not authenticated or token invalid"},
        403: {"description": "Caller does not hold the manager role"},
    },
)
def get_low_stock_report(
    current_user: User = Depends(require_role(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> List[LowStockReportItem]:
    """Thin route handler: validates manager auth, delegates to report_service."""
    return report_service.get_low_stock_report(db)


@router.get(
    "/near-expiry",
    response_model=List[NearExpiryReportItem],
    status_code=status.HTTP_200_OK,
    summary="Get near-expiry report",
    description="Manager-only per brief. Returns batches expiring within given number of days (default 30).",
    responses={
        401: {"description": "Not authenticated or token invalid"},
        403: {"description": "Caller does not hold the manager role"},
    },
)
def get_near_expiry_report(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(require_role(UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> List[NearExpiryReportItem]:
    """Thin route handler: checks Redis hot-read cache first, delegates to report_service on cache miss."""
    cache_key = f"cache:reports:near-expiry:days={days}"
    cached_val = get_cache(cache_key)
    if cached_val is not None:
        raw_items = json.loads(cached_val)
        return [NearExpiryReportItem.model_validate(item) for item in raw_items]

    result = report_service.get_near_expiry_report(db, days=days)
    json_str = json.dumps([item.model_dump() for item in result], default=str)
    set_cache(cache_key, json_str, expire_seconds=300)
    return result
