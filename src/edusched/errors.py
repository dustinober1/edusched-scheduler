"""Custom exception types for EduSched."""

from typing import Any, Optional


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(
        self,
        field: str,
        expected_format: str,
        actual_value: Any,
    ) -> None:
        self.field = field
        self.expected_format = expected_format
        self.actual_value = actual_value
        message = (
            f"Validation error in field '{field}': "
            f"expected {expected_format}, got {actual_value!r}"
        )
        super().__init__(message)


class InfeasibilityError(Exception):
    """Raised when a scheduling problem is infeasible."""

    def __init__(self, report: "InfeasibilityReport") -> None:  # noqa: F821
        self.report = report
        super().__init__(f"Scheduling problem is infeasible: {report.summary()}")


class BackendError(Exception):
    """Raised when a solver backend encounters an error."""

    def __init__(self, backend_name: str, error_details: str) -> None:
        self.backend_name = backend_name
        self.error_details = error_details
        message = f"Backend '{backend_name}' error: {error_details}"
        super().__init__(message)


class MissingOptionalDependency(Exception):
    """Raised when an optional dependency is required but not installed."""

    def __init__(self, feature: str, install_command: str) -> None:
        self.feature = feature
        self.install_command = install_command
        message = (
            f"Feature '{feature}' requires optional dependencies. "
            f"Install with: {install_command}"
        )
        super().__init__(message)
