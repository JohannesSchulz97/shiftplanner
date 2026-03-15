from __future__ import annotations
from collections.abc import Iterable

class ResourcesRequired:
    """The set of shared resource identifiers required by a task.

    Zero or more resources are allowed. Identifiers are normalized
    (stripped, lowercase) and deduplicated. Immutable after construction.
    """

    __slots__ = ("_resources",)

        def __init__(self, resources: Iterable[str] = ()) -> None:
        normalized: set[str] = set()
        for r in resources:
            if not isinstance(r, str):
                raise ValueError(f"Resource identifier must be a str, got {type(r).__name__!r}.")
            value = r.strip().lower()
            if not value:
                raise ValueError("Resource identifier must not be empty or whitespace.")
            normalized.add(value)
        self._resources: frozenset[str] = frozenset(normalized)

    @property
    def resources(self) -> frozenset[str]:
        """The immutable set of normalized resource identifiers."""
        return self._resources

    def contains(self, resource: str) -> bool:
        """Return True if the given resource identifier is required."""
        if not isinstance(resource, str):
            raise ValueError(f"Resource identifier must be a str, got {type(resource).__name__!r}.")
        return resource.strip().lower() in self._resources

    def is_empty(self) -> bool:
        """Return True if no resources are required."""
        return not self._resources

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ResourcesRequired):
            return self._resources == other._resources
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._resources)

    def __repr__(self) -> str:
        return f"ResourcesRequired({set(self._resources)!r})"


