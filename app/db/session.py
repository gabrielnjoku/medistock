from sqlmodel import Session, create_engine

from app.core.config import get_settings

settings = get_settings()

# echo=True in dev only — SQL logging is useful locally, noisy in prod.
engine = create_engine(settings.DATABASE_URL, echo=settings.ENV == "development")


def get_db():
    """Yield exactly one session per request. The `with` block closes
    the session whether the request succeeds, raises, or the service
    rolls back — routes and services never manage this lifecycle
    themselves.
    """
    with Session(engine) as session:
        yield session
