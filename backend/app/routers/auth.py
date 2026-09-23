"""Auth router — Phase 5 + 6.

POST /auth/login              — returns a JWT access token (any user)
POST /auth/users              — creates a new user account (admin only)
GET  /auth/me                 — returns the calling user's profile (any authenticated user)
GET  /auth/users              — list all users (admin only)
PATCH /auth/users/{user_id}  — update role or active status (admin only)
DELETE /auth/users/{user_id} — deactivate a user account (admin only, soft delete)
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase5 import User
from app.services.auth.auth_service import authenticate_user, create_access_token, create_user
from app.services.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    expires_in_minutes: int
    username:     str
    role:         str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role:     str = "analyst"

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ("analyst", "reviewer", "admin"):
            raise ValueError("role must be analyst, reviewer, or admin")
        return v


class UpdateUserRequest(BaseModel):
    role:      Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("analyst", "reviewer", "admin"):
            raise ValueError("role must be analyst, reviewer, or admin")
        return v


class UserOut(BaseModel):
    id:       str
    username: str
    role:     str
    is_active: bool

    @classmethod
    def from_orm(cls, u: User) -> "UserOut":
        return cls(id=str(u.id), username=u.username, role=u.role, is_active=u.is_active)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Obtain a JWT access token",
    description=(
        "Accepts form-encoded username and password. Returns a short-lived "
        "Bearer token. Tokens expire after the configured duration "
        "(default 60 minutes). No refresh tokens are issued."
    ),
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    from app.config import get_settings
    settings = get_settings()

    user = await authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        username=user.username,
        role=user.role,
        expires_in_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user (admin only)",
    description=(
        "Creates a new application user. Role must be one of: analyst, reviewer, admin. "
        "Requires an active admin JWT token."
    ),
)
async def create_user_endpoint(
    req: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    try:
        user = await create_user(db, req.username, req.password, req.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return UserOut.from_orm(user)


@router.get(
    "/users",
    response_model=List[UserOut],
    summary="List all users (admin only)",
    description="Returns a list of all registered user accounts. Requires admin role.",
)
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    result = await db.execute(select(User).order_by(User.username))
    return [UserOut.from_orm(u) for u in result.scalars().all()]


@router.patch(
    "/users/{user_id}",
    response_model=UserOut,
    summary="Update a user's role or active status (admin only)",
)
async def update_user(
    user_id: str,
    req: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid user ID format.")
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if req.role is not None:
        user.role = req.role
    if req.is_active is not None:
        user.is_active = req.is_active
    await db.commit()
    await db.refresh(user)
    return UserOut.from_orm(user)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a user account (admin only)",
    description="Soft-deletes by setting is_active=False. The record is preserved for audit integrity.",
)
async def deactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid user ID format.")
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.is_active = False
    await db.commit()


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get the currently authenticated user's profile",
)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.from_orm(current_user)


