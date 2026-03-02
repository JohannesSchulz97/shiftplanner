from datetime import time

class ShiftTemplate:
    """A reusable collection of shifts that defines a planning cycle structure.

    Shift Templates can be saved and reapplied across planning cycles.
    The planning horizon (daily, weekly, monthly, ad-hoc) is a parameter
    of the template, not a hardcoded concept.
    """

    def __init__(self, name: str, planning_horizon: str) -> None:
        self.name = self._validate(name, "name")
        self.planning_horizon = self._validate(planning_horizon, "planning_horizon")
        self._shifts: list[Shift] = []

class Shift:
    """A predefined time block within a planning period.


    Represents WHEN work can exist — not who is assigned to it.
    A shift is identified by a name and anchored to a specific day
    with a fixed start and end time.
    """

    def __init__(self, name: str, day: str, start_time: time, end_time: time) -> None:
        self.name = self._validate_str(name, "name")
        self.day = self._validate_str(day, "day")
        if end_time <= start_time:
            raise ValueError(
                f"end_time ({end_time}) must be strictly after start_time ({start_time})"
            )
        self.start_time = start_time
        self.end_time = end_time

    @staticmethod
    def _validate_str(value: str, label: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{label} must not be empty or whitespace")
        return stripped


    def duration_minutes(self) -> int:
        """Return the length of the shift in minutes."""
        start_total = self.start_time.hour * 60 + self.start_time.minute
        end_total = self.end_time.hour * 60 + self.end_time.minute
        return end_total - start_total

    def __repr__(self) -> str:
        return (
            f"Shift(name={self.name!r}, day={self.day!r}, "
            f"start_time={self.start_time}, end_time={self.end_time})"

             )      
