"""Pydantic schemas for user authentication."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserRegisterRequest(BaseModel):
    """Request body for user registration."""

    nickname: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=4, max_length=128)


class UserLoginRequest(BaseModel):
    """Request body for login."""

    nickname: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class UserIdentifyRequest(BaseModel):
    """Request body for user identification (legacy)."""

    nickname: str = Field(min_length=1, max_length=100)


class UserResponse(BaseModel):
    """Response body after user identification."""

    user_id: uuid.UUID = Field(validation_alias="id")
    nickname: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
