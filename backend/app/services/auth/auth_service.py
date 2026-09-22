"""Auth service — user creation, authentication, and JWT token management.

Design decisions:
  - bcrypt via passlib for password hashing (salted, work-factor configurable)
  - HS256 JWT for stateless token verification (no refresh tokens for hackathon scope)
  - JWT payload: sub (user_id as str), username, role, exp
  - JWT_SECRET_KEY must be set in .env — the Settings default flags this clearly
  - create_first_admin() is a one-shot bootstrap helper called by the migration;
    it is idempotent (skips if admin already exists)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.phase5 import User

logger = logging.getLogger(__name__)
settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(user: User) -> str:
    """Create a signed JWT for the given user."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub":      str(user.id),
        "username": user.username,
        "role":     user.role,
        "exp":      expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT.  Raises JWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> Optional[User]:
    """Return the User if credentials are valid, else None."""
    user = await get_user_by_username(db, username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    role: str = "analyst",
) -> User:
    """Create and persist a new user.  Raises ValueError on duplicate username."""
    existing = await get_user_by_username(db, username)
    if existing:
        raise ValueError(f"Username '{username}' is already taken.")
    if role not in ("analyst", "reviewer", "admin"):
        raise ValueError(f"Invalid role '{role}'. Must be analyst, reviewer, or admin.")

    user = User(
        username=username,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Created user %s (role=%s)", username, role)
    return user


async def ensure_bootstrap_admin(db: AsyncSession) -> None:
    """Idempotently create a default admin user if no users exist yet.

    Credentials are read from env so they can be changed before first start.
    Called from the FastAPI lifespan startup hook.
    """
    count_res = await db.execute(select(User))
    if count_res.scalars().first() is not None:
        return  # users already exist — skip

    import os
    admin_username = os.environ.get("BOOTSTRAP_ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "changeme123!")

    await create_user(db, admin_username, admin_password, role="admin")
    logger.warning(
        "Bootstrap admin created: username=%r. "
        "CHANGE THE PASSWORD before going to production.",
        admin_username,
    )
