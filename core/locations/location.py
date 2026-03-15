from __future__ import annotations


class Location:
    """A physical place associated with tasks and resources.

    Serves as a reference point for resource and task positioning within
    a schedule. Contains no travel logic or scheduling logic — it is a
    pure identity object used by other domain entities.
    """

    def __init__(self, location_id: str, name: str) -> None:
        if not isinstance(location_id, str) or not location_id.strip():
            raise ValueError("location_id must be a non-empty string.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string.")
        self._location_id: str = location_id.strip()
        self._name: str = name.strip()

    @property
    def location_id(self) -> str:
        """Unique identifier for this location."""
        return self._location_id

    @property
    def name(self) -> str:
        """Human-readable name of the location."""
        return self._name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Location):
            return self._location_id == other._location_id
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._location_id)

    def __repr__(self) -> str:
        return f"Location(location_id={self._location_id!r}, name={self._name!r})"
