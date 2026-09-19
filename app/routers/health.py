from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get(
    "/healthz",
    summary="Liveness check",
    description="Not part of the brief's API surface — used by docker-compose "
    "healthchecks and uptime monitoring only.",
)
def health_check() -> dict:
    return {"status": "ok"}
