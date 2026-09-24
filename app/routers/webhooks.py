import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.core.deps import get_db
from app.core.rate_limiter import RateLimiter
from app.schemas.webhook import DeliveryWebhookPayload, WebhookResponse
from app.services import webhook_service

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post(
    "/deliveries",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Receive supplier delivery webhook",
    description=(
        "Machine-to-machine endpoint (no JWT auth). Authenticates caller via HMAC-SHA256 "
        "X-Signature header. Deduplicates by event_id in processed_events table."
    ),
    dependencies=[Depends(RateLimiter(key_prefix="webhooks", requests_limit=60, window_seconds=60))],
    responses={
        200: {"description": "Duplicate ignored or orphan logged"},
        201: {"description": "Delivery successfully processed and stock updated"},
        401: {"description": "Invalid or missing X-Signature header"},
        429: {"description": "Rate limit exceeded (too many webhook requests)"},
        422: {"description": "Validation error on payload format"},
    },
)
async def delivery_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_signature: Optional[str] = Header(default=None, alias="X-Signature"),
    db: Session = Depends(get_db),
):
    """Thin route handler: reads raw body for HMAC signature verification, parses payload,
    and delegates execution to webhook_service.
    """
    raw_body = await request.body()
    try:
        data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        payload = DeliveryWebhookPayload.model_validate(data)
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": "422", "message": "Invalid webhook JSON body"}},
        )

    status_code, response_model = webhook_service.process_delivery_webhook(
        db=db,
        raw_body=raw_body,
        signature=x_signature,
        payload=payload,
        background_tasks=background_tasks,
    )
    return JSONResponse(status_code=status_code, content=response_model.model_dump())
