"""Validation run endpoints."""

import asyncio
import json as json_lib
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import StreamingResponse

from app.api.auth import CurrentUser
from app.config import settings
from app.db.database import async_session, get_db
from app.models.upload import Upload
from app.models.validation_result import ValidationIssue, ValidationRun
from app.schemas.validation import (
    ValidateBatchRequest,
    ValidateDocumentRequest,
    ValidationIssueSummary,
    ValidationRunRequest,
    ValidationRunResponse,
    ValidationRunStarted,
    ValidationSummary,
)
from app.services.schilling_service import SchillingFetchError, fetch_document_from_schilling
from app.services.validation_service import run_validation
from app.services.pdf_service import generate_validation_pdf
from app.services.annotated_pdf_service import generate_annotated_pdf
from app.services.batch_service import run_batch_validation, subscribe_progress
from app.validation.engine import ValidationEngine
from app.validation.parser import parse_file

router = APIRouter(prefix="/api/validations", tags=["validations"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

log = logging.getLogger(__name__)

# Heartbeat interval for SSE connections (seconds)
_HEARTBEAT_INTERVAL = 15

# Maximum concurrency for batch document processing
_BATCH_CONCURRENCY = 3


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

def _sse_event(event: str, data: dict) -> str:
    """Format a named SSE event."""
    return f"event: {event}\ndata: {json_lib.dumps(data)}\n\n"


def _sse_heartbeat() -> str:
    """Format a heartbeat SSE event."""
    return _sse_event("heartbeat", {"timestamp": int(time.time() * 1000)})


# ---------------------------------------------------------------------------
# Internal: process one document (fetch → save → parse → validate → stream)
# ---------------------------------------------------------------------------

async def _process_single_document(
    document_id: int,
    schilling_token: str,
    company_id: int,
    schilling_api_url: str,
) -> tuple[list[str], str | None]:
    """Fetch, parse, and validate one Schilling document.

    Returns a list of SSE-formatted strings plus an optional error code.
    On success the last event is ``validation_complete``; on failure an
    ``error`` event is emitted.
    """
    events: list[str] = []
    start_ms = int(time.time() * 1000)

    # ── 1. Fetch from Schilling ──
    try:
        pdf_bytes, metadata = await fetch_document_from_schilling(
            document_id=document_id,
            schilling_token=schilling_token,
            company_id=company_id,
            base_url=schilling_api_url,
        )
    except SchillingFetchError as exc:
        events.append(_sse_event("error", {
            "document_id": document_id,
            "message": str(exc),
            "error_code": exc.error_code,
        }))
        return events, exc.error_code

    filename = metadata.get("filename", f"document_{document_id}.pdf")
    size_bytes = metadata.get("size_bytes", len(pdf_bytes))
    file_format = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"

    events.append(_sse_event("document_fetched", {
        "document_id": document_id,
        "filename": filename,
        "format": file_format,
        "size_bytes": size_bytes,
    }))

    # ── 2. Save to disk + create Upload record ──
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    stored_name = f"{file_id}.{file_format}"
    stored_path = upload_dir / stored_name

    try:
        await asyncio.to_thread(stored_path.write_bytes, pdf_bytes)
    except Exception as exc:
        events.append(_sse_event("error", {
            "document_id": document_id,
            "message": f"Failed to save document: {exc}",
            "error_code": "VALIDATION_INTERNAL_ERROR",
        }))
        return events, "VALIDATION_INTERNAL_ERROR"

    # ── 3. Parse the file ──
    try:
        data = await asyncio.to_thread(parse_file, stored_path, file_format)
    except Exception as exc:
        events.append(_sse_event("error", {
            "document_id": document_id,
            "message": f"Failed to parse document: {exc}",
            "error_code": "DOCUMENT_PARSE_FAILED",
        }))
        return events, "DOCUMENT_PARSE_FAILED"

    row_count = len(data)

    # ── 4. Persist Upload + ValidationRun, run rules, persist issues ──
    async with async_session() as db:
        try:
            # Use the first available user as owner for the upload record.
            # In production, the frontend should pass a user context or use a
            # dedicated service account.
            from sqlalchemy import select as sa_select
            from app.models.user import User
            user_result = await db.execute(sa_select(User).limit(1))
            system_user = user_result.scalars().first()
            if not system_user:
                raise RuntimeError("No users in database — cannot create upload record")

            upload = Upload(
                id=file_id,
                user_id=system_user.id,
                filename=filename,
                file_path=str(stored_path),
                file_format=file_format,
                row_count=row_count,
            )
            db.add(upload)
            await db.flush()

            run = ValidationRun(
                upload_id=upload.id,
                status="running",
                started_at=datetime.now(UTC),
            )
            db.add(run)
            await db.flush()

            validation_id = str(run.id)

            # Emit validation_started
            engine = ValidationEngine()
            active_rules = engine.get_active_rules(["all"])
            events.append(_sse_event("validation_started", {
                "document_id": document_id,
                "validation_id": validation_id,
                "rules_count": len(active_rules),
            }))

            # ── 5. Run rules one by one with progress events ──
            all_issues = []
            real_rows = [r for r in data if r.get("dim1", "").strip().upper() != "SIMUL"]
            data_hygiene_rules = {"language_support", "unwanted_symbols", "text_within_margins"}

            for idx, rule in enumerate(active_rules, start=1):
                rows = data if rule.rule_id in data_hygiene_rules else real_rows
                issues = rule.validate(rows)
                all_issues.extend(issues)

                passed = not any(i.severity.value == "error" for i in issues)
                events.append(_sse_event("validation_progress", {
                    "document_id": document_id,
                    "validation_id": validation_id,
                    "rule_id": rule.rule_id,
                    "rule_name": rule.description,
                    "passed": passed,
                    "current": idx,
                    "total": len(active_rules),
                }))

            # ── 6. Persist issues ──
            error_count = sum(1 for i in all_issues if i.severity.value == "error")
            warning_count = sum(1 for i in all_issues if i.severity.value == "warning")
            info_count = sum(1 for i in all_issues if i.severity.value == "info")
            passed_count = len(active_rules) - len(
                {i.rule_id for i in all_issues if i.severity.value == "error"}
            )

            for issue in all_issues:
                db.add(ValidationIssue(
                    validation_run_id=run.id,
                    severity=issue.severity.value,
                    rule_id=issue.rule_id,
                    rule_description=issue.rule_description,
                    row_number=issue.row_number,
                    field=issue.field,
                    expected_value=issue.expected_value,
                    actual_value=issue.actual_value,
                    message=issue.message,
                    context=issue.context,
                ))

            run.status = "completed"
            run.rules_executed = len(active_rules)
            run.passed_count = passed_count
            run.error_count = error_count
            run.warning_count = warning_count
            run.info_count = info_count
            run.completed_at = datetime.now(UTC)
            await db.commit()

            duration_ms = int(time.time() * 1000) - start_ms
            events.append(_sse_event("validation_complete", {
                "document_id": document_id,
                "validation_id": validation_id,
                "error_count": error_count,
                "warning_count": warning_count,
                "info_count": info_count,
                "passed_count": passed_count,
                "total_rules": len(active_rules),
                "duration_ms": duration_ms,
            }))

            return events, None

        except Exception as exc:
            await db.rollback()
            log.exception("Validation failed for document %s", document_id)
            events.append(_sse_event("error", {
                "document_id": document_id,
                "message": f"Internal validation error: {exc}",
                "error_code": "VALIDATION_INTERNAL_ERROR",
            }))
            return events, "VALIDATION_INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# POST /api/validations/validate-document  (single Schilling document)
# ---------------------------------------------------------------------------

@router.post("/validate-document")
async def validate_document(body: ValidateDocumentRequest) -> StreamingResponse:
    """Validate a single document fetched from the Schilling API.

    Fetches the document using the provided Schilling credentials, runs all
    validation rules, and streams progress as SSE events.
    """

    async def event_generator():
        events, _error = await _process_single_document(
            document_id=body.document_id,
            schilling_token=body.schilling_token,
            company_id=body.company_id,
            schilling_api_url=body.schilling_api_url,
        )
        for evt in events:
            yield evt

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# POST /api/validations/validate-batch  (multiple Schilling documents)
# ---------------------------------------------------------------------------

@router.post("/validate-batch")
async def validate_batch(body: ValidateBatchRequest) -> StreamingResponse:
    """Validate multiple documents fetched from the Schilling API.

    Documents are processed in parallel (up to _BATCH_CONCURRENCY at a time).
    Per-document SSE events may interleave. Ends with a ``batch_complete`` event.
    """

    async def event_generator():
        start_ms = int(time.time() * 1000)
        completed = 0
        failed = 0
        semaphore = asyncio.Semaphore(_BATCH_CONCURRENCY)

        async def _process_with_limit(doc_id: int):
            async with semaphore:
                return await _process_single_document(
                    document_id=doc_id,
                    schilling_token=body.schilling_token,
                    company_id=body.company_id,
                    schilling_api_url=body.schilling_api_url,
                )

        tasks = [
            asyncio.create_task(_process_with_limit(doc_id))
            for doc_id in body.document_ids
        ]

        for coro in asyncio.as_completed(tasks):
            events, error_code = await coro
            for evt in events:
                yield evt
            if error_code:
                failed += 1
            else:
                completed += 1

        duration_ms = int(time.time() * 1000) - start_ms
        yield _sse_event("batch_complete", {
            "total": len(body.document_ids),
            "completed": completed,
            "failed": failed,
            "duration_ms": duration_ms,
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Existing endpoints (unchanged)
# ---------------------------------------------------------------------------


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
    validation_id: uuid.UUID, db: DbSession
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
    validation_id: uuid.UUID, db: DbSession,
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
    validation_id: uuid.UUID, db: DbSession,
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


# ---------------------------------------------------------------------------
# Batch validation endpoints
# ---------------------------------------------------------------------------

from pydantic import BaseModel


class BatchValidationRequest(BaseModel):
    upload_ids: list[uuid.UUID]


@router.post("/batch", status_code=201)
async def trigger_batch_validation(
    body: BatchValidationRequest,
    current_user: CurrentUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> dict:
    """Trigger validation for multiple uploads as a batch.

    Returns immediately with a batch_id. Progress is streamed via SSE at
    ``GET /api/validations/batch/{batch_id}/progress``.
    """
    if not body.upload_ids:
        raise HTTPException(status_code=400, detail="No upload IDs provided")

    # Verify all uploads exist and belong to the user
    for uid in body.upload_ids:
        result = await db.execute(select(Upload).where(Upload.id == uid))
        upload = result.scalars().first()
        if not upload:
            raise HTTPException(status_code=404, detail=f"Upload {uid} not found")

    batch_id = str(uuid.uuid4())

    # Schedule background processing
    background_tasks.add_task(
        run_batch_validation,
        batch_id=batch_id,
        upload_ids=body.upload_ids,
        user_id=current_user.id,
    )

    return {
        "batch_id": batch_id,
        "status": "processing",
        "validations": [],  # Will be populated via SSE events
    }


@router.get("/batch/{batch_id}/progress")
async def batch_progress_sse(batch_id: str) -> StreamingResponse:
    """SSE endpoint streaming real-time progress for a batch validation.

    Auth is passed via ``?token=`` query parameter since EventSource cannot set
    headers. For simplicity, we rely on the batch_id being unguessable (UUID4).
    """

    async def event_generator():
        async for event in subscribe_progress(batch_id):
            data = json_lib.dumps(event)
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
