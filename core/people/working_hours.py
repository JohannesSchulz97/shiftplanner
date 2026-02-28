class WorkingHours:
    """Maximum working hour constraints for a person.

    Defines upper bounds on how many hours a person may be assigned,
    both within a single day and across an entire planning period
    (e.g. a week or schedule cycle).
    """

    def __init__(self, max_per_day: float, max_per_period: float) -> None:
        self.max_per_day = self._validate(max_per_day, "max_per_day")
        self.max_per_period = self._validate(max_per_period, "max_per_period")

    @staticmethod
    def _validate(value: float, label: str) -> float:
        if value <= 0:
            raise ValueError(f"{label} must be a positive number, got {value}")
        return float(value)

    def allows_day(self, hours: float) -> bool:
        """Return True if the given hours fit within the daily limit."""
        return hours <= self.max_per_day

    def allows_period(self, hours: float) -> bool:
        """Return True if the given hours fit within the planning-period limit."""
        return hours <= self.max_per_period

    def __repr__(self) -> str:
        return f"WorkingHours(max_per_day={self.max_per_day}, max_per_period={self.max_per_period})"
