"""Optional authentication (JWT + bcrypt).

``AUTH_REQUIRED=false`` by default: the application is usable anonymously and
every conversation is then owned by a null user. Flip the flag to require a
bearer token on the write endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import settings
from .db.models import User
from .db.session import get_db

_bearer = HTTPBearer(auto_error=False)

# bcrypt only considers the first 72 bytes of a password.
_BCRYPT_MAX = 72


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")[:_BCRYPT_MAX]
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:_BCRYPT_MAX], hashed.encode("ascii"))
    except Exception:  # noqa: BLE001 - malformed hash, wrong encoding, etc.
        return False


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {"sub": user.id, "role": user.role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """Return the authenticated user, or ``None`` when auth is optional."""
    token = credentials.credentials if credentials else None
    if not token:
        if settings.auth_required:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
        return None
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, payload.get("sub", ""))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return user


def require_admin(user: User | None = Depends(get_current_user)) -> User:
    if user is None or user.role != "admin":
        if settings.auth_required:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
        # Auth disabled: local development mode permits admin routes.
        return user  # type: ignore[return-value]
    return user


def ensure_admin_user(db: Session) -> User:
    """Create the bootstrap admin on first boot."""
    existing = db.query(User).filter(User.role == "admin").first()
    if existing is not None:
        return existing
    email = settings.admin_email
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(settings.admin_password),
            display_name=settings.admin_name,
            role="admin",
        )
        db.add(user)
        db.commit()
    return user
