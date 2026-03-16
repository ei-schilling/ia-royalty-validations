"""Pydantic schemas for user identification."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserIdentifyRequest(BaseModel):
    """Request body for user identification."""
    nickname: str = Field(min_length=1, max_length=100)


class UserResponse(BaseModel):
    """Response body after user identification."""
    user_id: uuid.UUID = Field(validation_alias="id")
    nickname: str
    created_at: datetime

    model_config = {"from_attributes": True}
