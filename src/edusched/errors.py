"""Custom exception types for EduSched."""

from typing import Any, Optional


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: Optional[str] = None,
        field: Optional[str] = None,
        expected_format: Optional[str] = None,
        actual_value: Optional[Any] = None,
    ) -> None:
        if message is None:
            # Backwards compatibility - construct message from fields
            if field is None or expected_format is None or actual_value is None:
                raise ValueError("Must provide either message or all field parameters")
            message = (
                f"Validation error in field '{field}': "
                f"expected {expected_format}, got {actual_value!r}"
            )

        self.message = message
        self.field = field
        self.expected_format = expected_format
        self.actual_value = actual_value
        super().__init__(message)


class InfeasibilityError(Exception):
    """Raised when a scheduling problem is infeasible."""

    def __init__(self, report: "InfeasibilityReport") -> None:  # noqa: F821
        self.report = report
        super().__init__(f"Scheduling problem is infeasible: {report.summary()}")


class BackendError(Exception):
    """Raised when a solver backend encounters an error."""

    def __init__(self, message: str, backend_name: Optional[str] = None, error_details: Optional[str] = None) -> None:
        if backend_name and error_details:
            # Backwards compatibility
            message = f"Backend '{backend_name}' error: {error_details}"
            self.backend_name = backend_name
            self.error_details = error_details
        else:
            self.message = message
            self.backend_name = backend_name
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
