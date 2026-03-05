from __future__ import annotations
from datetime import datetime


class ResourceAssignment:
    """Schedule-time allocation of a resource to a person.

    Represents the exclusive use of a shared resource within a specific time
    window. A resource can only be assigned to one person at a time — overlapping
    assignments for the same resource are invalid.
    """

    def __init__(
        self,
        resource_id: str,
        person_id: str,
        start_datetime: datetime,
        end_datetime: datetime,
    ) -> None:
        if start_datetime >= end_datetime:
            raise ValueError(
                f"start_datetime ({start_datetime}) must be strictly before "
                f"end_datetime ({end_datetime})."
            )
        self.resource_id: str = resource_id
        self.person_id: str = person_id
        self.start_datetime: datetime = start_datetime
        self.end_datetime: datetime = end_datetime

    def overlaps(self, other: ResourceAssignment) -> bool:
        """Return True if this assignment overlaps another in time.

        Overlap rule:
            self.start < other.end AND self.end > other.start
        Adjacent intervals (end == start) do NOT overlap.
        """
        return (
            self.start_datetime < other.end_datetime
            and self.end_datetime > other.start_datetime
        )

    def __repr__(self) -> str:
        return (
            f"ResourceAssignment("
            f"resource_id={self.resource_id!r}, "
            f"person_id={self.person_id!r}, "
            f"start={self.start_datetime!r}, "
            f"end={self.end_datetime!r})"
        )


def validate_resource_exclusivity(assignments: list[ResourceAssignment]) -> None:
    """Raise ValueError if any resource is assigned to multiple people simultaneously.

    Groups assignments by resource_id and checks each group for overlapping
    intervals. Raises on the first conflict found.
    """
    by_resource: dict[str, list[ResourceAssignment]] = {}
    for a in assignments:
        by_resource.setdefault(a.resource_id, []).append(a)

    for resource_id, group in by_resource.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a.overlaps(b):
                    raise ValueError(
                        f"Resource {resource_id!r} has overlapping assignments: "
                        f"{a.person_id!r} ({a.start_datetime}–{a.end_datetime}) "
                        f"conflicts with "
                        f"{b.person_id!r} ({b.start_datetime}–{b.end_datetime})."
                    )
