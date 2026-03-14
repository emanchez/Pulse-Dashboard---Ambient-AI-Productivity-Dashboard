from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt as _bcrypt
import jwt as pyjwt
from jwt.exceptions import InvalidTokenError
from fastapi import HTTPException, status

from .config import get_settings

settings = get_settings()

_ISSUER = "pulse-api"
_AUDIENCE = "pulse-client"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return _bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT with iss/aud claims and an 8-hour TTL by default."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "iss": _ISSUER,
        "aud": _AUDIENCE,
    }
    token: str = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and fully validate a JWT (signature, expiry, iss, aud)."""
    try:
        payload: dict[str, Any] = pyjwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=_AUDIENCE,
            issuer=_ISSUER,
        )
        return payload
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
