from __future__ import annotations
import math


class Duration:
    """Total hours required to complete a task.

    A strictly positive, finite value expressed in hours.
    Immutable after construction.
    """

    __slots__ = ("_hours",)

    def __init__(self, hours: int | float) -> None:
        value = float(hours)
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"Duration must be a finite number, got {hours!r}.")
        if value <= 0:
            raise ValueError(f"Duration must be strictly positive, got {hours!r}.")
        self._hours: float = value

    @property
    def hours(self) -> float:
        """The total required work time in hours."""
        return self._hours

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Duration):
            return math.isclose(self._hours, other._hours)
        return NotImplemented
    
    def __hash__(self) -> int:
            return hash(self._hours)
    
    def __repr__(self) -> str:
        return f"Duration(hours={self._hours})"


