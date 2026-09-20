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
