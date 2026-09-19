from typing import Iterator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlmodel import Session

from app.core.security import decode_access_token
from app.db.session import get_db as _get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

# tokenUrl is where /docs sends the "Authorize" form — it doesn't have
# to be implemented yet for this to be wired up correctly.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_db() -> Iterator[Session]:
    """Re-exported from app.db.session so every router imports its
    dependencies from exactly one place: app.core.deps.
    """
    yield from _get_db()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the bearer token and load the matching user.

    401, never 403, for anything wrong with the token itself (missing,
    expired, forged, or pointing at a user that no longer exists). 403
    is reserved for require_role: you ARE who the token says, you're
    just not allowed to do this.
    """
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    email = payload.get("sub")
    user = UserRepository(db).get_by_email(email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return user


def require_role(*allowed_roles: UserRole):
    """Dependency FACTORY, not a single function — use as
    Depends(require_role(UserRole.MANAGER)).

    A factory because roles-per-route vary, and the brief's "staff"
    grouping on GET /inventory and GET /prescriptions/{id} isn't one
    fixed role — it's however you decide to define it, e.g.
    Depends(require_role(UserRole.PHARMACIST, UserRole.DOCTOR, UserRole.MANAGER)).
    This keeps that decision visible at the route, not buried in a
    copy-pasted if-chain inside the route body.
    """

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted for this role")
        return user

    return checker
