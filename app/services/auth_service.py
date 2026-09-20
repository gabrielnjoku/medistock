from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import Token, UserCreate, UserLogin


def register_user(db: Session, payload: UserCreate) -> User:
    """Register a new staff or supplier user.

    Enforces business rules:
      1. Duplicate check: email must be unique across all active users.
         Raises 409 Conflict if already taken.
      2. Security: Plaintext password is never persisted. We compute a
         salted bcrypt hash before creating the record.
      3. Persistence: Delegated to UserRepository which manages the commit.
    """
    user_repo = UserRepository(db)
    existing_user = user_repo.get_by_email(payload.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    hashed_password = hash_password(payload.password)
    new_user = User(
        email=payload.email,
        password_hash=hashed_password,
        role=payload.role,
    )
    return user_repo.create(new_user)


def authenticate_user(db: Session, payload: UserLogin) -> Token:
    """Authenticate credentials and issue a signed JWT access token.

    Enforces business rules:
      1. Looks up the user by email.
      2. Compares the plaintext password against the stored bcrypt hash.
         Raises 401 Unauthorized on non-existent email or invalid password.
         (Generic error message to avoid account enumeration attacks).
      3. Embeds user email (`sub`) and role (`role`) in the token payload
         so downstream requests can verify permissions without DB queries.
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(subject=user.email, role=user.role.value)
    return Token(access_token=access_token, token_type="bearer")
