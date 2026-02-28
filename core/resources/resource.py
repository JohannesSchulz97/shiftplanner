class Resource:
    """A shared physical item required for tasks or coverage slots.

    Resources are persistent across planning cycles. They are available by
    default; unavailability must be explicitly declared for specific time windows.
    Resources can only be assigned to one person at a time.
    """

    def __init__(self, name: str) -> None:
        self.name = self._validate(name, "name")
        self._unavailable_windows: list[tuple[str, str]] = []

    @staticmethod
    def _validate(value: str, label: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{label} must not be empty or whitespace")
        return stripped

    def mark_unavailable(self, start: str, end: str) -> None:
        """Mark this resource as unavailable for a specific time window."""
        start = self._validate(start, "start")
        end = self._validate(end, "end")
        self._unavailable_windows.append((start, end))

    def clear_unavailability(self) -> None:
        """Remove all unavailability windows, restoring full availability."""
        self._unavailable_windows.clear()

    @property
    def unavailable_windows(self) -> list[tuple[str, str]]:
        """Return a copy of all declared unavailability windows."""
        return list(self._unavailable_windows)

    def __repr__(self) -> str:
        return f"Resource(name={self.name!r}, unavailable_windows={self._unavailable_windows!r})"
