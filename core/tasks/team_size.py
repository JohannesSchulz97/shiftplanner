from __future__ import annotations


class TeamSize:
    """Minimum and maximum number of people that may be assigned to a task.

    Represents an inclusive range [min_size, max_size].
    Defaults to exactly one person. Immutable after construction.
    """

    __slots__ = ("_min", "_max")

    def __init__(self, min_size: int = 1, max_size: int = 1) -> None:
        if not isinstance(min_size, int) or isinstance(min_size, bool):
            raise ValueError(f"min_size must be an int, got {type(min_size).__name__!r}.")
        if not isinstance(max_size, int) or isinstance(max_size, bool):
            raise ValueError(f"max_size must be an int, got {type(max_size).__name__!r}.")
        if min_size < 1:
            raise ValueError(f"min_size must be >= 1, got {min_size}.")
        if max_size < min_size:
            raise ValueError(f"max_size ({max_size}) must be >= min_size ({min_size}).")
        self._min: int = min_size
        self._max: int = max_size

    @property
    def min_size(self) -> int:
        """Minimum number of people required."""
        return self._min

    @property
    def max_size(self) -> int:
        """Maximum number of people allowed."""
        return self._max

    @property
    def is_single_person(self) -> bool:
        """Return True if the task requires exactly one person."""
        return self._min == 1 and self._max == 1

    @property
    def allows_multiple(self) -> bool:
        """Return True if the task allows more than one person."""
        return self._max > 1

    def accepts(self, count: int) -> bool:
        if not isinstance(count, int) or isinstance(count, bool):
            raise ValueError("count must be an int.")
        return self._min <= count <= self._max

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TeamSize):
            return self._min == other._min and self._max == other._max
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._min, self._max))

    def __repr__(self) -> str:
        return f"TeamSize(min_size={self._min}, max_size={self._max})"


