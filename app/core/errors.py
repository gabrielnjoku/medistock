import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _error_body(code: str, message: str, request_id: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def register_exception_handlers(app: FastAPI) -> None:
    """One error shape everywhere: {"error": {"code", "message", "request_id"}}.

    Registered once, here, so no route or service ever builds this dict
    by hand — raise HTTPException(status_code, detail) from a service
    and it comes out the other side in the shared shape automatically.
    A service should never return a 200 with an error dict inside it.
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code=str(exc.status_code), message=str(exc.detail), request_id=request_id),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        errors = exc.errors()
        msg = errors[0].get("msg", "Validation error") if errors else "Validation error"
        if errors and "loc" in errors[0]:
            field = " -> ".join(str(loc) for loc in errors[0]["loc"] if str(loc) != "body")
            msg = f"Validation error for '{field}': {msg}" if field else f"Validation error: {msg}"
        return JSONResponse(
            status_code=422,
            content=_error_body(code="422", message=msg, request_id=request_id),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Catches anything a service didn't turn into an HTTPException —
        # callers never see a raw traceback or a framework-default shape.
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=500,
            content=_error_body(code="500", message="Internal server error", request_id=request_id),
        )
