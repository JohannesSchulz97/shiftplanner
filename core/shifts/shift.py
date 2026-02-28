class Shift:
    """A single named time block within a planning cycle.

    Represents a specific work window on a specific day, defined by
    its name, day, start time, and end time.
    """

    def __init__(self, name: str, day: str, start_time: str, end_time: str) -> None:
        self.name = self._validate(name, "name")
        self.day = self._validate(day, "day")
        self.start_time = self._validate(start_time, "start_time")
        self.end_time = self._validate(end_time, "end_time")

    @staticmethod
    def _validate(value: str, label: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{label} must not be empty or whitespace")
        return stripped

    def __repr__(self) -> str:
        return (
            f"Shift(name={self.name!r}, day={self.day!r}, "
            f"start_time={self.start_time!r}, end_time={self.end_time!r})"
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
