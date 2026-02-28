class RestPeriod:
    """Minimum required rest time between two consecutive assignments for a person.

    Enforces a mandatory gap (in hours) between the end of one assignment
    and the start of the next, ensuring legal or contractual rest requirements
    are respected during scheduling.
    """

    def __init__(self, minimum_hours: float) -> None:
        self.minimum_hours = self._validate(minimum_hours)

    @staticmethod
    def _validate(value: float) -> float:
        if value <= 0:
            raise ValueError(f"minimum_hours must be a positive number, got {value}")
        return float(value)

    def allows_gap(self, hours_between: float) -> bool:
        """Return True if the gap between assignments meets the minimum rest requirement."""
        return hours_between >= self.minimum_hours

    def required_gap(self) -> float:
        """Return the configured minimum rest hours."""
        return self.minimum_hours

    def __repr__(self) -> str:
        return f"RestPeriod(minimum_hours={self.minimum_hours})"
