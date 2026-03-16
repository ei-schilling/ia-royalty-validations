"""Validation service — orchestrates validation runs against uploaded files."""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload import Upload
from app.models.validation_result import ValidationRun, ValidationIssue
from app.validation.engine import ValidationEngine
from app.validation.parser import parse_file


async def run_validation(
    db: AsyncSession,
    upload: Upload,
    rules_filter: list[str],
) -> ValidationRun:
    """Execute validation rules against the uploaded file and persist results."""
    run = ValidationRun(upload_id=upload.id, status="running", started_at=datetime.now(timezone.utc))
    db.add(run)
    await db.flush()

    try:
        data = parse_file(Path(upload.file_path), upload.file_format)
        engine = ValidationEngine()
        issues = engine.run(data, rules_filter)

        error_count = sum(1 for i in issues if i.severity.value == "error")
        warning_count = sum(1 for i in issues if i.severity.value == "warning")
        info_count = sum(1 for i in issues if i.severity.value == "info")
        rules_executed = len(engine.get_active_rules(rules_filter))
        passed_count = rules_executed - len({i.rule_id for i in issues if i.severity.value == "error"})

        for issue in issues:
            db_issue = ValidationIssue(
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
            )
            db.add(db_issue)

        run.status = "completed"
        run.rules_executed = rules_executed
        run.passed_count = passed_count
        run.warning_count = warning_count
        run.error_count = error_count
        run.info_count = info_count
    except Exception as exc:
        run.status = "failed"
        db.add(ValidationIssue(
            validation_run_id=run.id,
            severity="error",
            rule_id="system",
            rule_description="System error during validation",
            message=str(exc),
            context={"error_type": type(exc).__name__},
        ))
        run.error_count = 1

    run.completed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(run)
    return run
