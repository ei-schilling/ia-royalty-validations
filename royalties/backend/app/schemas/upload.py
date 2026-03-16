"""Pydantic schemas for file uploads."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response body after successful file upload."""
    upload_id: uuid.UUID = Field(validation_alias="id")
    filename: str
    file_format: str
    row_count: int | None
    status: str = "uploaded"
    uploaded_at: datetime

    model_config = {"from_attributes": True}
