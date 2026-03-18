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


class ValidationRunBrief(BaseModel):
    """Compact validation run info for history listing."""

    validation_id: uuid.UUID = Field(validation_alias="id")
    status: str
    errors: int = Field(validation_alias="error_count")
    warnings: int = Field(validation_alias="warning_count")
    infos: int = Field(validation_alias="info_count")
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class UploadHistoryItem(BaseModel):
    """Upload with its latest validation run info."""

    upload_id: uuid.UUID = Field(validation_alias="id")
    filename: str
    file_format: str
    row_count: int | None
    uploaded_at: datetime
    validations: list[ValidationRunBrief] = Field(validation_alias="validation_runs")

    model_config = {"from_attributes": True}
