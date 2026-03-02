class Limitations:
    """Explicit exclusions that prevent a person from performing certain assignments.

    Limitations are independent of availability — they represent hard constraints
    (e.g. legal restrictions, certifications, conflicts) that block assignment
    regardless of whether the person is otherwise available.
    """

    def __init__(self) -> None:
        self._limitations: set[str] = set()

    @staticmethod
    def _validate(value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("limitation must not be empty or whitespace")
        return stripped

    def add(self, limitation: str) -> None:
        """Add a limitation by identifier. Duplicates are ignored."""
        self._limitations.add(self._validate(limitation))

    def remove(self, limitation: str) -> None:
        """Remove a limitation. Silent no-op if not present."""
        self._limitations.discard(self._validate(limitation))

    def has(self, limitation: str) -> bool:
        """Return True if the given limitation is active."""
        return self._validate(limitation) in self._limitations

    def __repr__(self) -> str:
        return f"Limitations(limitations={self._limitations!r})"
