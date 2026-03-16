"""Authentication / user identification endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserIdentifyRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/identify", response_model=UserResponse)
async def identify_user(body: UserIdentifyRequest, db: DbSession) -> User:
    """Register or find a user by nickname. Returns existing user if nickname taken."""
    result = await db.execute(select(User).where(User.nickname == body.nickname))
    user = result.scalars().first()
    if user:
        return user

    user = User(nickname=body.nickname)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
