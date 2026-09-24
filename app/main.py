import uuid

from fastapi import FastAPI, Request

from app.core.errors import register_exception_handlers
from app.core.middleware import RequestTimingMiddleware
from app.routers import auth, dispenses, health, inventory, prescriptions, products, reports, stock, webhooks

app = FastAPI(title="MediStock", version="0.1.0")

register_exception_handlers(app)
app.add_middleware(RequestTimingMiddleware)


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(reports.router)
app.include_router(prescriptions.router)
app.include_router(dispenses.router)
app.include_router(stock.router)
app.include_router(webhooks.router)
