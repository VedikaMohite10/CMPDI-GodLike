"""FastAPI dependency factories for JWT authentication and RBAC.

Usage:
    from app.services.auth.dependencies import get_current_user, require_role

    # Any authenticated user:
    @router.get("/foo")
    async def foo(current_user: User = Depends(get_current_user)):
        ...

    # Reviewer or admin only:
    @router.post("/bar")
    async def bar(current_user: User = Depends(require_role("reviewer", "admin"))):
        ...
"""
from __future__ import annotations

import uuid
import logging
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase5 import User
from app.services.auth.auth_service import decode_token, get_user_by_id

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=True)

_ROLE_HIERARCHY = {"analyst": 0, "reviewer": 1, "admin": 2}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate the Bearer JWT and return the authenticated User.

    Raises HTTP 401 if:
      - No token is provided (HTTPBearer auto_error handles this)
      - Token is expired, invalid, or malformed
      - The user referenced by the token no longer exists or is inactive
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise JWTError("Missing sub claim")
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*allowed_roles: str) -> Callable:
    """Return a FastAPI dependency that enforces role membership.

    Usage:
        Depends(require_role("reviewer", "admin"))

    Raises HTTP 403 if the current user's role is not in allowed_roles.
    """
    allowed_set = set(allowed_roles)

    async def _check(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Action requires role in {sorted(allowed_set)}. "
                    f"Your role is '{current_user.role}'."
                ),
            )
        return current_user

    return _check
