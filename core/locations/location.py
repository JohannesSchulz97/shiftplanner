class Location:
    """A physical location associated with tasks and resources."""

    def __init__(self, name: str) -> None:
        self.name = self._validate(name, "name")

    @staticmethod
    def _validate(value: str, label: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{label} must not be empty or whitespace")
        return stripped

    def __repr__(self) -> str:
        return f"Location(name={self.name!r})"


class TravelMatrix:
    """Travel time (in minutes) between pairs of locations.

    Defines how long it takes to travel from one location to another.
    Used by the solver to enforce travel time buffers between consecutive
    assignments at different locations.
    """

    def __init__(self) -> None:
        self._times: dict[tuple[str, str], float] = {}

    @staticmethod
    def _validate(value: str, label: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{label} must not be empty or whitespace")
        return stripped

    def set_travel_time(self, from_location: str, to_location: str, minutes: float) -> None:
        """Set the travel time in minutes between two locations."""
        from_location = self._validate(from_location, "from_location")
        to_location = self._validate(to_location, "to_location")
        if minutes < 0:
            raise ValueError(f"minutes must be non-negative, got {minutes}")
        self._times[(from_location, to_location)] = float(minutes)

    def get_travel_time(self, from_location: str, to_location: str) -> float | None:
        """Return travel time in minutes, or None if not defined."""
        from_location = self._validate(from_location, "from_location")
        to_location = self._validate(to_location, "to_location")
        return self._times.get((from_location, to_location))

    def __repr__(self) -> str:
        return f"TravelMatrix(routes={len(self._times)})"
