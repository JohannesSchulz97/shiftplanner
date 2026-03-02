from __future__ import annotations
from enum import Enum


class PriorityLevel(Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"


class Priority:
    """The scheduling priority of a task: required or optional.

    REQUIRED → task must be assigned during the planning period.
    OPTIONAL → task is desirable but may be left unassigned.
    Immutable after construction.
    """

    __slots__ = ("_level",)

    def __init__(self, level: PriorityLevel | str = PriorityLevel.OPTIONAL) -> None:
        if isinstance(level, PriorityLevel):
            self._level: PriorityLevel = level
        elif isinstance(level, str):
            normalized = level.strip().lower()
            try:
                self._level = PriorityLevel(normalized)
            except ValueError:
                valid = [e.value for e in PriorityLevel]
                raise ValueError(f"Invalid priority {level!r}. Must be one of {valid}.")
        else:
            raise ValueError(f"Priority requires a PriorityLevel or str, got {type(level).__name__!r}.")

    @property
    def level(self) -> PriorityLevel:
        """The underlying priority level."""
        return self._level

    @property
    def is_required(self) -> bool:
        """Return True if the task must be assigned."""
        return self._level is PriorityLevel.REQUIRED

    @property
    def is_optional(self) -> bool:
        """Return True if the task may be left unassigned."""
        return self._level is PriorityLevel.OPTIONAL

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Priority):
            return self._level == other._level        
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._level)

    def __repr__(self) -> str:
        return f"Priority({self._level.value!r})"


