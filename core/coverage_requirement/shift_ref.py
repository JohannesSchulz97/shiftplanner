from __future__ import annotations


class ShiftRef:
    """Reference to the shift a coverage requirement applies to.

    Holds a normalized shift identifier (stripped, lowercase).
    Does not contain a Shift object — only its identifier.
    Immutable after construction.
    """

    __slots__ = ("_value",)

    def __init__(self, shift_id: str) -> None:
        if not isinstance(shift_id, str):
            raise ValueError(f"shift_id must be a str, got {type(shift_id).__name__!r}.")
        normalized = shift_id.strip().lower()
        if not normalized:
            raise ValueError("shift_id must not be empty or whitespace.")
        self._value: str = normalized

    @property
    def value(self) -> str:
        """The normalized shift identifier."""
        return self._value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ShiftRef):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"ShiftRef({self._value!r})"
