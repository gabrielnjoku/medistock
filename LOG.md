# LOG

Daily 5-liner — what I did / what broke / what I learned / what's next / who did what.

## Day 1 — 2026-09-18
- Did: Read brief, drafted paper ERD, endpoint table, and hard problem explanation.
- Broke: Initial confusion on locking order for FEFO dispense.
- Learned: FEFO requires SELECT ... FOR UPDATE ordered by expiry_date ascending to avoid deadlocks.
- Next: Instructor review and repo bootstrap.
- Who did what: Gabriel & Loveth paired on ERD and hard problem notes.

## Day 2 — 2026-09-19
- Did: Initialized FastAPI project, Docker setup, Alembic migrations, and health check test.
- Broke: Docker compose Postgres port clash on local port 5432.
- Learned: Dev/prod parity via docker compose and pydantic-settings twelve-factor config.
- Next: Day 3 JWT authentication and RBAC.
- Who did what: Gabriel set up Docker and CI; Loveth set up config and base database session.

## Day 3 — 2026-09-20
- Did: Implemented JWT auth (register & login), native bcrypt password hashing, `get_current_user`, `require_role(...)` RBAC, and test-first 401/403 suite.
- Broke: Passlib 1.7.4 crashed against modern bcrypt on 72-byte string, and SQLModel 0.0.22 missed annotations on Python 3.14 PEP 649.
- Learned: Direct bcrypt (`hashpw`/`checkpw`) avoids passlib wrapper bugs; dependency factory pattern keeps multi-role checks visible at router level.
- Next: Day 4 core inventory models (products, batches with expiry index) and first two epics.
- Who did what: Gabriel and Loveth paired on Router->Service->Repository layering, security dependencies, and acceptance criteria tests.

## Day 4 — 2026-09-21
- Did: Implemented Products and Batches SQLModel tables, Alembic migration 0002, repositories, services, routers, and 16 new pytest tests (26 total passing).
- Broke: Missing email-validator dependency when running Pydantic EmailStr validation in fresh environment.
- Learned: Indexing `expiry_date` on the `batches` table is critical for FEFO queries; Pydantic validation schemas guarantee 422 errors on negative stock input before reaching services.
- Next: Day 5 Prescriptions & Dispenses epics and first viva checkpoint.
- Who did what: Gabriel built products/batches models & migrations; Loveth built inventory and reports services/routers; both paired on unit testing.

## Day 5 — 2026-09-22
- Did: Implemented Prescriptions, PrescriptionLines, and StockMovements tables, Alembic migration 0003, services, routers, 11 new pytest tests (37 total passing), and completed Day 5 Viva.
- Broke: Initial stock adjustment allowed negative inventory balances without raising a 422 error.
- Learned: Validating balance bounds (`batch.qty_on_hand + delta >= 0`) inside single service transactions guarantees data integrity before persisting movement audit rows.
- Next: Day 6 Webhook endpoint with signature verification & idempotency.
- Who did what: Gabriel implemented prescriptions and stock movements; Loveth built stock adjustment services and test suite; both completed Day 5 Viva practice.

## Day 6 — 2026-09-23
- Did: Implemented POST /api/v1/webhooks/deliveries, ProcessedEvents table, Alembic migration 0004, HMAC signature verification, deduplication, orphan logging, and 4 acceptance criteria tests (41 total passing).
- Broke: Timing attack vulnerability when comparing raw HMAC signatures using standard equality `==`.
- Learned: `hmac.compare_digest` prevents constant-time side-channel attacks; saving `event_id` in `processed_events` even for orphans ensures retry-safety without duplicated processing.
- Next: Day 7 Swap-and-extend morning & SSE live stock-alert stream.
- Who did what: Gabriel built webhook security & signature verification; Loveth built ProcessedEvents deduplication & test suite; both paired on background task offloading.
