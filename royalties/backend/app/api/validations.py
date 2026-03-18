"""Validation run endpoints."""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import CurrentUser
from app.db.database import get_db
from app.models.upload import Upload
from app.models.validation_result import ValidationIssue, ValidationRun
from app.schemas.validation import (
    ValidationIssueSummary,
    ValidationRunRequest,
    ValidationRunResponse,
    ValidationRunStarted,
    ValidationSummary,
)
from app.services.validation_service import run_validation
from app.services.pdf_service import generate_validation_pdf
from app.services.annotated_pdf_service import generate_annotated_pdf

router = APIRouter(prefix="/api/validations", tags=["validations"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/{upload_id}/run", response_model=ValidationRunStarted, status_code=201)
async def trigger_validation(
    upload_id: uuid.UUID,
    _current_user: CurrentUser,
    db: DbSession,
    body: Optional[ValidationRunRequest] = None,
) -> dict:
    """Trigger a validation run on a previously uploaded file."""
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalars().first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    rules_filter = body.rules if body else ["all"]
    validation_run = await run_validation(db, upload, rules_filter)
    return {"validation_id": validation_run.id, "status": validation_run.status}


@router.get("/{validation_id}", response_model=ValidationRunResponse)
async def get_validation(
    validation_id: uuid.UUID, _current_user: CurrentUser, db: DbSession
) -> dict:
    """Get full validation results including all issues."""
    result = await db.execute(
        select(ValidationRun)
        .where(ValidationRun.id == validation_id)
        .options(
            selectinload(ValidationRun.issues),
            selectinload(ValidationRun.upload),
        )
    )
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Validation run not found")

    total_rows = run.upload.row_count or 0 if run.upload else 0
    return {
        "validation_id": run.id,
        "upload_id": run.upload_id,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "summary": ValidationSummary(
            total_rows=total_rows,
            rules_executed=run.rules_executed,
            passed_checks=run.passed_count,
            warnings=run.warning_count,
            errors=run.error_count,
            infos=run.info_count,
        ),
        "issues": [ValidationIssueSummary.model_validate(issue) for issue in run.issues],
    }


@router.get("/{validation_id}/issues", response_model=list[ValidationIssueSummary])
async def get_validation_issues(
    validation_id: uuid.UUID,
    _current_user: CurrentUser,
    db: DbSession,
    severity: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[ValidationIssue]:
    """Get paginated validation issues, optionally filtered by severity."""
    # Verify run exists
    run_result = await db.execute(select(ValidationRun).where(ValidationRun.id == validation_id))
    if not run_result.scalars().first():
        raise HTTPException(status_code=404, detail="Validation run not found")

    query = select(ValidationIssue).where(ValidationIssue.validation_run_id == validation_id)
    if severity:
        query = query.where(ValidationIssue.severity == severity)
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{validation_id}/pdf")
async def download_validation_pdf(
    validation_id: uuid.UUID, _current_user: CurrentUser, db: DbSession,
) -> Response:
    """Generate and return a PDF report for a validation run."""
    result = await db.execute(
        select(ValidationRun)
        .where(ValidationRun.id == validation_id)
        .options(selectinload(ValidationRun.issues), selectinload(ValidationRun.upload))
    )
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Validation run not found")

    filename = run.upload.filename if run.upload else "unknown"
    total_rows = run.upload.row_count or 0 if run.upload else 0

    issues_dicts = [
        {
            "severity": issue.severity,
            "rule_id": issue.rule_id,
            "rule_description": issue.rule_description,
            "row_number": issue.row_number,
            "field": issue.field,
            "expected_value": issue.expected_value,
            "actual_value": issue.actual_value,
            "message": issue.message,
        }
        for issue in run.issues
    ]

    pdf_bytes = generate_validation_pdf(
        filename=filename,
        validation_id=str(validation_id),
        started_at=run.started_at,
        completed_at=run.completed_at,
        total_rows=total_rows,
        rules_executed=run.rules_executed,
        passed_checks=run.passed_count,
        errors=run.error_count,
        warnings=run.warning_count,
        infos=run.info_count,
        issues=issues_dicts,
    )

    safe_name = filename.rsplit(".", 1)[0] if "." in filename else filename
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_report.pdf"'},
    )


@router.get("/{validation_id}/annotated-pdf")
async def download_annotated_pdf(
    validation_id: uuid.UUID, _current_user: CurrentUser, db: DbSession,
) -> Response:
    """Generate a PDF of the original data with validation issues highlighted."""
    result = await db.execute(
        select(ValidationRun)
        .where(ValidationRun.id == validation_id)
        .options(selectinload(ValidationRun.issues), selectinload(ValidationRun.upload))
    )
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Validation run not found")

    upload = run.upload
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    issues_dicts = [
        {
            "severity": issue.severity,
            "rule_id": issue.rule_id,
            "rule_description": issue.rule_description,
            "row_number": issue.row_number,
            "field": issue.field,
            "expected_value": issue.expected_value,
            "actual_value": issue.actual_value,
            "message": issue.message,
        }
        for issue in run.issues
    ]

    pdf_bytes = generate_annotated_pdf(
        file_path=upload.file_path,
        file_format=upload.file_format,
        filename=upload.filename,
        validation_id=str(validation_id),
        total_rows=upload.row_count or 0,
        issues=issues_dicts,
    )

    safe_name = upload.filename.rsplit(".", 1)[0] if "." in upload.filename else upload.filename
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_annotated.pdf"'},
    )
