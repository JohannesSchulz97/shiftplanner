from __future__ import annotations


class TravelTimeMatrix:
    """Travel durations between named locations, expressed in minutes.

    Defines how long it takes to travel from one location to another.
    Used later by schedule validation to enforce travel-time constraints
    between consecutive assignments. Contains no schedule logic itself.
    """

    def __init__(self) -> None:
        self._matrix: dict[tuple[str, str], int] = {}

    def set_travel_time(
        self,
        from_location_id: str,
        to_location_id: str,
        minutes: int,
    ) -> None:
        """Store the travel time in minutes from one location to another.

        Raises ValueError if minutes is negative.
        """
        if minutes < 0:
            raise ValueError(f"minutes must be >= 0, got {minutes}.")
        self._matrix[(from_location_id, to_location_id)] = minutes

    def get_travel_minutes(
        self,
        from_location_id: str,
        to_location_id: str,
    ) -> int:
        """Return travel time in minutes between two locations.

        Returns 0 for same-location pairs.
        Raises ValueError if the pair has no defined travel time.
        """
        if from_location_id == to_location_id:
            return 0
        key = (from_location_id, to_location_id)
        if key not in self._matrix:
            raise ValueError(
                f"No travel time defined from {from_location_id!r} to {to_location_id!r}."
            )
        return self._matrix[key]

    def __repr__(self) -> str:
        return f"TravelTimeMatrix(pairs={len(self._matrix)})"
