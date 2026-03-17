"""Validation run and issue models for storing validation results."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("uploads.id"))
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending|running|completed|failed
    rules_executed: Mapped[int] = mapped_column(Integer, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    info_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    upload = relationship("Upload", back_populates="validation_runs")
    issues = relationship("ValidationIssue", back_populates="validation_run")


class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    validation_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("validation_runs.id"))
    severity: Mapped[str] = mapped_column(String(10))  # error, warning, info
    rule_id: Mapped[str] = mapped_column(String(50))
    rule_description: Mapped[str] = mapped_column(Text)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expected_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    actual_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    validation_run = relationship("ValidationRun", back_populates="issues")
