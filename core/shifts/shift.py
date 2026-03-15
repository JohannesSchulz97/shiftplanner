from datetime import time


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

    @staticmethod
    def _validate(value: str, label: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{label} must not be empty or whitespace")
        return stripped

    def add_shift(self, shift: Shift) -> None:
        """Add a shift to this template. Duplicate names are not allowed."""
        if any(s.name == shift.name for s in self._shifts):
            raise ValueError(f"A shift named {shift.name!r} already exists in this template")
        self._shifts.append(shift)

    def remove_shift(self, name: str) -> None:
        """Remove a shift by name. Silent no-op if not found."""
        self._shifts = [s for s in self._shifts if s.name != name]

    def get_shift(self, name: str) -> Shift | None:
        """Return the shift with the given name, or None if not found."""
        return next((s for s in self._shifts if s.name == name), None)

    @property
    def shifts(self) -> list[Shift]:
        """Return a copy of the shifts list."""
        return list(self._shifts)

    def __repr__(self) -> str:
        return (
            f"ShiftTemplate(name={self.name!r}, "
            f"planning_horizon={self.planning_horizon!r}, shifts={self._shifts!r})"
        )
