# MediStock

Pharmacy inventory system — Lion Moons capstone (Gabriel & Loveth).

## Stack
FastAPI · SQLModel · PostgreSQL + Alembic · Firestore (stock_events, expiry_alerts feed) · Redis · Docker Compose

## Running locally

    cp .env.example .env   # fill in real values — .env is gitignored, never commit it
    docker compose up --build

- API root / docs: http://localhost:8000/docs
- Health check: http://localhost:8000/healthz

## Running migrations

    docker compose exec api alembic upgrade head

To add a new migration later:

    docker compose exec api alembic revision --autogenerate -m "add batches table"

## Project layout

    app/
      core/          config (pydantic-settings), security (hashing/JWT),
                      the shared error shape, and reusable dependencies
                      (get_db, get_current_user, require_role)
      db/             engine/session setup, SQLModel metadata aggregator
      models/         SQLModel table classes (one file per table)
      schemas/        request/response Pydantic models — never the same
                      class as the table model
      repositories/   one file per table — every query against that
                      table lives here and nowhere else
      services/       business rules — routers call these, never the DB
                      directly
      routers/        thin — parse the request, call one service
                      function, return

    migrations/       Alembic — versions/ holds one file per schema change
    tests/            pytest — test DB only, never the dev database

## The hard problem
<!-- TODO — write this yourself, in your own words, before any dispense
     logic is committed (grading rule 1). Cover: why idempotency matters
     for POST /dispenses, how the row-level locking + FEFO ordering
     works, and the 409 vs 422 split. Don't paste generated prose here —
     draft it, then get it reviewed. -->

## Why this design
<!-- TODO — same rule. Outline the points, then write the prose
     yourself: why routers/services/repositories, why one error shape,
     why one transaction per business action, etc. -->
