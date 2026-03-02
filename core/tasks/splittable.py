from __future__ import annotations


class Splittable:
    """Whether a task may be distributed across multiple non-consecutive shifts.

    True  → task may be split across shifts.
    False → task must be completed in one continuous block.
    Immutable after construction.
    """

    __slots__ = ("_value",)

    def __init__(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValueError(f"Splittable requires a bool, got {type(value).__name__!r}.")
        self._value: bool = value

    @property
    def value(self) -> bool:
        """The raw splittability flag."""
        return self._value

    @property
    def is_splittable(self) -> bool:
        """Return True if the task may be split across non-consecutive shifts."""
        return self._value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Splittable):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"Splittable({self._value})"


