from __future__ import annotations


class InfeasibilityReport:
    """Summarizes the conflicts that prevented a feasible schedule from being generated.

    Collects constraint failures encountered during solving, providing structured
    access to both machine-readable constraint names and human-readable messages.
    Contains no solver or validation logic — it is a pure reporting structure.
    """

    def __init__(self) -> None:
        self.failed_constraints: list[str] = []
        self.messages: list[str] = []

    def add_failure(self, constraint_name: str, message: str) -> None:
        """Record a constraint failure with its name and descriptive message."""
        self.failed_constraints.append(constraint_name)
        self.messages.append(message)

    def to_dict(self) -> dict:
        """Return a serializable representation of all recorded failures."""
        return {
            "failed_constraints": self.failed_constraints,
            "messages": self.messages,
        }

    @classmethod
    def from_exception(cls, exception: Exception) -> "InfeasibilityReport":
        """Create a report from a single exception.

        Uses the exception class name as the constraint identifier and the
        string representation of the exception as the message.
        """
        report = cls()
        report.add_failure(
            constraint_name=type(exception).__name__,
            message=str(exception),
        )
        return report

    def __repr__(self) -> str:
        return (
            f"InfeasibilityReport("
            f"failures={len(self.failed_constraints)})"
        )
