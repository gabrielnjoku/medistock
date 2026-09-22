from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from typing import Any, Optional

import bcrypt
from jose import jwt

from app.core.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt with a freshly generated salt.
    Never store plaintext passwords in the database.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a candidate plaintext password against an existing bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, role: str) -> str:
    """subject is the user's email; role is embedded in the token so
    require_role can check it directly without a DB round-trip on
    every single request.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises jose.JWTError on anything invalid or expired — the caller
    (get_current_user) is responsible for turning that into a 401.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def compute_webhook_signature(raw_body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 hex digest of raw request body using secret key."""
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def verify_webhook_signature(raw_body: bytes, signature_header: Optional[str], secret: str) -> bool:
    """Verify X-Signature header using hmac.compare_digest to prevent timing attacks.
    Returns True if valid, False otherwise.
    """
    if not signature_header:
        return False
    expected = signature_header.removeprefix("sha256=") if signature_header.startswith("sha256=") else signature_header
    computed = compute_webhook_signature(raw_body, secret)
    return hmac.compare_digest(expected.lower(), computed.lower())
