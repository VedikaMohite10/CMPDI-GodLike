"""Auth router — Phase 5.

POST /auth/login       — returns a JWT access token (any user)
POST /auth/users       — creates a new user account (admin only)
GET  /auth/me          — returns the calling user's profile (any authenticated user)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, field_validator
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
    "/me",
    response_model=UserOut,
    summary="Get the currently authenticated user's profile",
)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.from_orm(current_user)
