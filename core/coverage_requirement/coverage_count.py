from __future__ import annotations


class CoverageCount:
    """Minimum number of people required to satisfy a coverage requirement.

    Represents a demand threshold (e.g. "at least 2 drivers").
    Immutable after construction.
    """

    __slots__ = ("_value",)

    def __init__(self, count: int) -> None:
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError(f"count must be an int, got {type(count).__name__!r}.")
        if count < 1:
            raise ValueError(f"count must be >= 1, got {count}.")
        self._value: int = count

    @property
    def value(self) -> int:
        """The minimum required number of people."""
        return self._value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CoverageCount):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"CoverageCount({self._value})"
