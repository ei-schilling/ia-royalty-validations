"""Abstract base class for validation rules and shared data types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from enum import Enum


class Severity(Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue found during a rule check."""

    severity: Severity
    rule_id: str
    rule_description: str
    message: str
    row_number: int | None = None
    field: str | None = None
    expected_value: str | None = None
    actual_value: str | None = None
    context: dict = dataclass_field(default_factory=dict)


class BaseRule(ABC):
    """Abstract base class that all validation rules must implement."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique identifier for this rule (e.g., 'missing_titles')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this rule checks."""
        ...

    @abstractmethod
    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        """Run this rule against the parsed statement data.

        Args:
            statement_data: List of row dictionaries from the parsed file.

        Returns:
            List of issues found. Empty list means the rule passed.
        """
        ...
