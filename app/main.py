import uuid

from fastapi import FastAPI, Request

from app.core.errors import register_exception_handlers
from app.routers import auth, health, inventory, prescriptions, products, reports, stock

app = FastAPI(title="MediStock", version="0.1.0")

register_exception_handlers(app)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Every response carries a request_id — the shared error shape
    (app/core/errors.py) reuses this same id, so a user-reported error
    and a server log line can be matched up without guessing by
    timestamp.
    """
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(reports.router)
app.include_router(prescriptions.router)
app.include_router(stock.router)
