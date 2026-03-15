from __future__ import annotations


class Location:
    """Physical location where a task takes place.

    Stored as a normalized (stripped, lowercase) string identifier.
    Two locations with the same normalized name are considered equal.
    Immutable after construction.
    """

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        if not isinstance(name, str):
            raise ValueError(f"Location requires a str, got {type(name).__name__!r}.")
        normalized = name.strip().lower()
        if not normalized:
            raise ValueError("Location name must not be empty or whitespace.")
        self._name: str = normalized

    @property
    def name(self) -> str:
        """The normalized location identifier."""
        return self._name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Location):
            return self._name == other._name
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._name)

    def __repr__(self) -> str:
        return f"Location({self._name!r})"


