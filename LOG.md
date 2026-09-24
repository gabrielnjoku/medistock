# LOG

Daily 5-liner — what I did / what broke / what I learned / what's next / who did what.

## Day 1 — 2026-09-18
- Did: Read brief, drafted paper ERD, endpoint table, and hard problem explanation.
- Broke: Initial confusion on locking order for FEFO dispense.
- Learned: FEFO requires SELECT ... FOR UPDATE ordered by expiry_date ascending to avoid deadlocks.
- Next: Instructor review and repo bootstrap.
- Who did what: Gabriel & Loveth paired on ERD and hard problem notes.

## Day 2 — 2026-09-19
- Did: Initialized FastAPI project, Docker setup, Alembic migrations, and health check test (Commit: Initial commit).
- Broke: Docker compose Postgres port clash on local port 5432.
- Learned: Dev/prod parity via docker compose and pydantic-settings twelve-factor config.
- Next: Day 3 JWT authentication and RBAC.
- Who did what: Gabriel set up Docker, Alembic, and CI pipeline; Loveth set up config and base database session.

## Day 3 — 2026-09-20
- Did: Implemented JWT auth (register & login), native bcrypt password hashing, `get_current_user`, `require_role(...)` RBAC, and test auth suite (Commit: added test auth).
- Broke: Passlib 1.7.4 crashed against modern bcrypt on 72-byte string.
- Learned: Direct bcrypt (`hashpw`/`checkpw`) avoids passlib wrapper bugs; dependency factory pattern keeps multi-role checks visible at router level.
- Next: Day 4 core inventory models (products, batches with expiry index) and core tables.
- Who did what: Loveth built auth tests & security helpers; Gabriel implemented JWT endpoints and RBAC dependencies.

## Day 4 — 2026-09-21
- Did: Built Core tables (Products, Batches), Accounts & Inventory epics, Alembic migration 0002, and fixed GitHub workflow annotations (Commits: feat/Core tables + Accounts & Inventory epics, issue/github workflow annotation).
- Broke: Missing email-validator dependency when running Pydantic EmailStr validation in fresh environment.
- Learned: Indexing `expiry_date` on the `batches` table is critical for fast FEFO queries; Pydantic validation schemas guarantee 422 errors on negative stock input.
- Next: Day 5 Supplier Delivery Webhooks & Dispensing records.
- Who did what: Gabriel built products/batches SQLModel tables & CI workflow fix; Loveth built inventory and reports services/routers; both paired on unit testing.

## Day 5 — 2026-09-22
- Did: Implemented Supplier Delivery Webhook (HMAC signature verification & idempotency) and Dispensing Records (Commits: feat/Supplier Delivery Webhook & Idempotency, Dispensing and Records).
- Broke: Timing attack vulnerability when comparing raw HMAC signatures using standard string equality `==`.
- Learned: `hmac.compare_digest` prevents constant-time side-channel attacks; saving `event_id` in `processed_events` ensures retry-safety without duplicate inventory ingestion.
- Next: Day 6 Hard problem dispense endpoint concurrency & live SSE stock alert stream.
- Who did what: Gabriel implemented webhook HMAC security & ProcessedEvents deduplication; Loveth built dispensing records repository, models, and test cases.

## Day 6 — 2026-09-23
- Did: Implemented FEFO dispense endpoint (`POST /api/v1/dispenses`), row-level locking (`SELECT ... FOR UPDATE`), SSE stock alert stream (`GET /api/v1/stock/alerts/stream`), and gitignore cleanup (Commits: feat/dispense endpoint & hard problem concurrency, Added SSE Stock Alert Stream, updated .gitignore).
- Broke: Race condition in simultaneous dispenses draining the last remaining unit.
- Learned: `SELECT ... FOR UPDATE` ordered by `expiry_date ASC, id ASC` serializes concurrent transactions cleanly; SHA-256 fingerprinting catches parameter tampering.
- Next: Day 7 Scheduled sweeper job, Redis cache, rate limiting, and request timing middleware.
- Who did what: Gabriel built dispense FEFO transaction & idempotency logic; Loveth built live SSE broadcaster & alert streaming endpoint.

## Day 7 — 2026-09-24
- Did: Implemented daily scheduled expiry alert sweeper job, Redis hot-read caching with write invalidation matrix, IP rate limiting (`429` + `Retry-After`), and request timing middleware (`X-Request-ID` & `X-Response-Time`) (Commit: Added scheduled job, redis cache, rate limiting, middleware).
- Broke: Missing `Retry-After` HTTP header when rate limit threshold was breached.
- Learned: Cache invalidation on batch write paths (`POST /batches`, `POST /dispenses`, `POST /adjust`) prevents stale inventory reads.
- Next: Day 8 Firestore movement timeline, expiry alerts feed, seed script, single error shape audit, and OpenAPI polish.
- Who did what: Loveth implemented Redis cache helper, rate limiter dependency, and timing middleware; Gabriel integrated write invalidation calls & sweeper job.

## Day 8 — 2026-09-24
- Did: Implemented Firestore data layer (`stock_events` movement timeline, `expiry_alerts` feed with in-memory fallback), one-command seed script (`seed.py`), single error shape audit (`{"error": {"code", "message", "request_id"}}`), and README architectural rationale (Commit: feat/firestore events timeline & expiry alerts).
- Broke: Linter missing name error `firestore` when referencing enum direction, and SQL migration duplicate enum `userrole` error on fresh postgres container boot.
- Learned: Passing string literal `"DESCENDING"` avoids SDK scope issues; `create_type=False` on Postgres enum columns prevents redundant `CREATE TYPE` errors during Alembic migrations.
- Next: Final viva defense practice and demo deployment.
- Who did what: Gabriel implemented Firestore client wrapper, seed script, and error shape exception handlers; Loveth built Firestore endpoints, updated README architectural rationale, and verified 57/57 test suite pass rate.
