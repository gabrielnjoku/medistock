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

## Architectural Trade-Offs: Firestore vs PostgreSQL

### Why Firestore for `stock_events` & `expiry_alerts` vs PostgreSQL?

 MediStock splits its data layer across PostgreSQL and Google Cloud Firestore based on workload characteristics:

1. **PostgreSQL (Transactional OLTP Core)**:
   - Handles `users`, `products`, `batches`, `prescriptions`, `dispenses`, and `idempotency_keys`.
   - **Why**: These entities demand strict ACID transactional guarantees, strong foreign key constraints, and row-level locking (`SELECT ... FOR UPDATE`) to prevent race conditions during FEFO batch stock deductions.

2. **Firestore (Append-Only Event Stream & Query Feed)**:
   - Handles `stock_events` (movement audit timeline) and `expiry_alerts` (daily near-expiry feed).
   - **Why `stock_events` in Firestore**: Stock movements are high-frequency, append-only logs. Writing every granular event directly into PostgreSQL causes table bloat, index fragmentation, and database lock overhead. Firestore document collections offer seamless horizontal scaling for historical audit trails without impacting relational query performance.
   - **Why `expiry_alerts` in Firestore**: Near-expiry batches are pre-computed daily by a background sweeper job (`expiry_sweeper.py`) and published to Firestore. Frontend dashboards and mobile client apps can query low-latency Firestore documents without placing load on PostgreSQL's connection pool or active transaction engine.

## The hard problem
<!-- Idempotent dispense with FEFO batch row-level locking -->
- `POST /api/v1/dispenses` requires an `Idempotency-Key` header. Duplicate request keys with identical payload return the cached response without re-executing stock movements. Duplicate keys with a modified body return `422 Unprocessable Entity`.
- FEFO (First-Expired, First-Out) stock selection acquires row locks (`SELECT ... FOR UPDATE`) on non-expired batches ordered by `expiry_date ASC, id ASC`.
- Insufficient non-expired stock rolls back the transaction atomically and returns `409 Conflict`.
