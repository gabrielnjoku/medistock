from sqlmodel import Session

from app.schemas.user import UserCreate
from app.models.user import User  # noqa: F401 — used once you implement this


def register_user(db: Session, payload: UserCreate) -> User:
    """Register a new user.

    Deliberately left as a TODO — not because it's hard, but because
    grading rule 1 says no business logic before your Day 1-2 paper
    artifacts (ERD, endpoint list, hard-problem writeup) are signed
    off. This is plain CRUD and a good first service to write once
    they are:

      1. UserRepository(db).get_by_email(payload.email) — if a user
         already exists, raise HTTPException(409, ...) (the shared
         error shape in app/core/errors.py handles the rest).
      2. hash_password(payload.password) from app.core.security —
         never store the raw password.
      3. Build a User(...) with the hash and role, save it via
         UserRepository(db).create(...).
      4. Return the saved User — the router's response_model=UserRead
         takes care of dropping password_hash before it goes out.

    One transaction per business action: UserRepository.create commits
    once. Don't call db.commit() again in here — if you do, you no
    longer have "one commit, rollback on any failure," you have two
    commits that can each partially succeed.
    """
    raise NotImplementedError("Write this once your Day 1-2 paper artifacts are signed off.")
