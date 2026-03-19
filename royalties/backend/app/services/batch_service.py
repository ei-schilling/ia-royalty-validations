"""Batch processing service — orchestrates multi-file validation with progress streaming."""

import asyncio
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session
from app.models.upload import Upload
from app.models.validation_result import ValidationIssue, ValidationRun
from app.validation.engine import ValidationEngine
from app.validation.parser import parse_file

# In-memory progress store: batch_id -> asyncio.Queue of events
_progress_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)


def _register_listener(batch_id: str) -> asyncio.Queue:
    """Register a new SSE listener for a batch."""
    q: asyncio.Queue = asyncio.Queue()
    _progress_queues[batch_id].append(q)
    return q


def _remove_listener(batch_id: str, q: asyncio.Queue) -> None:
    """Remove an SSE listener."""
    queues = _progress_queues.get(batch_id, [])
    if q in queues:
        queues.remove(q)
    if not queues:
        _progress_queues.pop(batch_id, None)


async def _broadcast(batch_id: str, event: dict) -> None:
    """Broadcast a progress event to all listeners of a batch."""
    for q in _progress_queues.get(batch_id, []):
        await q.put(event)


async def subscribe_progress(batch_id: str):
    """Async generator yielding progress events for SSE streaming."""
    q = _register_listener(batch_id)
    try:
        while True:
            event = await q.get()
            yield event
            if event.get("type") == "batch_complete":
                break
    finally:
        _remove_listener(batch_id, q)


async def run_batch_validation(
    batch_id: str,
    upload_ids: list[uuid.UUID],
    user_id: uuid.UUID,
) -> None:
    """Background task: validate each file sequentially with progress events.

    Opens its own DB session since this runs outside the request lifecycle.
    """
    from sqlalchemy import select

    results: list[dict] = []

    try:
        for idx, upload_id in enumerate(upload_ids):
            # Store locals eagerly — ORM attributes expire after rollback/commit
            filename: str = "unknown"
            file_path: str = ""
            file_format: str = ""

            async with async_session() as db:
                try:
                    # Fetch upload
                    res = await db.execute(select(Upload).where(Upload.id == upload_id))
                    upload = res.scalars().first()
                    if not upload:
                        await _broadcast(batch_id, {
                            "type": "file_error",
                            "upload_id": str(upload_id),
                            "filename": filename,
                            "progress_pct": 0,
                            "message": "Upload not found",
                        })
                        continue

                    # Eagerly copy all needed attributes to locals
                    filename = upload.filename
                    file_path = upload.file_path
                    file_format = upload.file_format
                    upload_pk = upload.id

                    # file_start
                    await _broadcast(batch_id, {
                        "type": "file_start",
                        "upload_id": str(upload_id),
                        "filename": filename,
                        "progress_pct": 0,
                    })

                    # Parsing phase
                    await _broadcast(batch_id, {
                        "type": "file_parsing",
                        "upload_id": str(upload_id),
                        "filename": filename,
                        "progress_pct": 20,
                    })

                    # Run sync parser in a thread to avoid blocking the event loop
                    data = await asyncio.to_thread(parse_file, Path(file_path), file_format)

                    # Validating phase
                    await _broadcast(batch_id, {
                        "type": "file_validating",
                        "upload_id": str(upload_id),
                        "filename": filename,
                        "progress_pct": 50,
                    })

                    # Create validation run
                    run = ValidationRun(
                        upload_id=upload_pk,
                        status="running",
                        started_at=datetime.now(UTC),
                    )
                    db.add(run)
                    await db.flush()
                    run_id = run.id  # capture before commit expires it

                    # Run sync validation engine in a thread
                    engine = ValidationEngine()
                    issues = await asyncio.to_thread(engine.run, data, ["all"])

                    error_count = sum(1 for i in issues if i.severity.value == "error")
                    warning_count = sum(1 for i in issues if i.severity.value == "warning")
                    info_count = sum(1 for i in issues if i.severity.value == "info")
                    rules_executed = len(engine.get_active_rules(["all"]))
                    passed_count = rules_executed - len(
                        {i.rule_id for i in issues if i.severity.value == "error"}
                    )

                    # Progress update
                    await _broadcast(batch_id, {
                        "type": "file_validating",
                        "upload_id": str(upload_id),
                        "filename": filename,
                        "progress_pct": 80,
                    })

                    for issue in issues:
                        db_issue = ValidationIssue(
                            validation_run_id=run_id,
                            severity=issue.severity.value,
                            rule_id=issue.rule_id,
                            rule_description=issue.rule_description,
                            row_number=issue.row_number,
                            field=issue.field,
                            expected_value=issue.expected_value,
                            actual_value=issue.actual_value,
                            message=issue.message,
                            context=issue.context,
                        )
                        db.add(db_issue)

                    run.status = "completed"
                    run.rules_executed = rules_executed
                    run.passed_count = passed_count
                    run.warning_count = warning_count
                    run.error_count = error_count
                    run.info_count = info_count
                    run.completed_at = datetime.now(UTC)
                    await db.commit()

                    summary = {
                        "upload_id": str(upload_id),
                        "validation_id": str(run_id),
                        "filename": filename,
                        "status": "completed",
                        "errors": error_count,
                        "warnings": warning_count,
                        "infos": info_count,
                        "passed": passed_count,
                        "rules_executed": rules_executed,
                    }
                    results.append(summary)

                    await _broadcast(batch_id, {
                        "type": "file_complete",
                        "upload_id": str(upload_id),
                        "filename": filename,
                        "progress_pct": 100,
                        "summary": summary,
                    })

                except Exception as exc:
                    # Try to mark the run as failed if we created one
                    try:
                        await db.rollback()
                    except Exception:
                        pass

                    await _broadcast(batch_id, {
                        "type": "file_error",
                        "upload_id": str(upload_id),
                        "filename": filename,
                        "progress_pct": 0,
                        "message": str(exc),
                    })
    finally:
        # Always send batch_complete so the SSE stream closes gracefully
        await _broadcast(batch_id, {
            "type": "batch_complete",
            "upload_id": "",
            "filename": "",
            "progress_pct": 100,
            "message": f"Processed {len(upload_ids)} files",
            "summary": {
                "total": len(upload_ids),
                "completed": len(results),
                "failed": len(upload_ids) - len(results),
            },
        })
