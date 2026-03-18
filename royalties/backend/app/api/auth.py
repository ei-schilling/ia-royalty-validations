"""Authentication endpoints: register, login, current user."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── helpers ──────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _create_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    """Decode JWT and return the authenticated user."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalars().first()
    if user is None:
        raise credentials_exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ── endpoints ────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: UserRegisterRequest, db: DbSession) -> dict:
    """Create a new user account."""
    result = await db.execute(select(User).where(User.nickname == body.nickname))
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="Nickname already taken")

    user = User(nickname=body.nickname, password_hash=_hash_password(body.password))
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return {
        "access_token": _create_token(user.id),
        "token_type": "bearer",
        "user": user,
    }


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLoginRequest, db: DbSession) -> dict:
    """Authenticate with nickname + password and receive a JWT."""
    result = await db.execute(select(User).where(User.nickname == body.nickname))
    user = result.scalars().first()

    if not user or not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid nickname or password")

    return {
        "access_token": _create_token(user.id),
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> User:
    """Return the currently authenticated user."""
    return current_user
