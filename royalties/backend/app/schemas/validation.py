"""Pydantic schemas for validation runs and issues."""

import uuid
from datetime import datetime


from typing import Optional, Dict
from pydantic import BaseModel, Field


class ValidationRunRequest(BaseModel):
    """Request body for triggering a validation run."""

    rules: list[str] = ["all"]


# ---------------------------------------------------------------------------
# Schilling document validation (external integration)
# ---------------------------------------------------------------------------


class ValidateDocumentRequest(BaseModel):
    """Request body for single-document validation via Schilling API."""

    document_id: int = Field(..., description="Schilling DocumentId from the recipient row")
    schilling_token: Optional[str] = Field(None, description="Ignored — backend authenticates directly")
    company_id: int = Field(..., description="Schilling company ID")
    schilling_api_url: str = Field(..., min_length=1, description="Schilling API base URL (no trailing slash)")


class ValidateBatchRequest(BaseModel):
    """Request body for batch document validation via Schilling API."""

    document_ids: list[int] = Field(..., min_length=1, description="Array of Schilling DocumentId values")
    schilling_token: Optional[str] = Field(None, description="Ignored — backend authenticates directly")
    company_id: int = Field(..., description="Schilling company ID")
    schilling_api_url: str = Field(..., min_length=1, description="Schilling API base URL (no trailing slash)")


class ValidationIssueSummary(BaseModel):
    """Single validation issue in the response."""

    id: uuid.UUID
    severity: str
    rule_id: str
    rule_description: str
    row_number: Optional[int]
    field: Optional[str]
    expected_value: Optional[str]
    actual_value: Optional[str]
    message: str
    context: Optional[Dict]

    model_config = {"from_attributes": True}


class ValidationSummary(BaseModel):
    """Aggregated counts for a validation run."""

    total_rows: int
    rules_executed: int
    passed_checks: int
    warnings: int
    errors: int
    infos: int


class ValidationRunResponse(BaseModel):
    """Full validation run result."""

    validation_id: uuid.UUID
    upload_id: uuid.UUID
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    summary: ValidationSummary
    issues: list[ValidationIssueSummary]

    model_config = {"from_attributes": True}


class ValidationRunStarted(BaseModel):
    """Response when a validation run is triggered."""

    validation_id: uuid.UUID
    status: str
