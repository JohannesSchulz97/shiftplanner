from __future__ import annotations
from datetime import datetime

VALID_ASSIGNMENT_TYPES = frozenset({"task", "coverage"})


class Assignment:
    """Atomic scheduling unit linking a person to a task or coverage slot during a shift.

    Represents the fundamental decision made by the scheduler:
    a specific person is assigned to either a task or a coverage requirement,
    within a defined shift, at a specific location and time window.
    """

    def __init__(
        self,
        person_id: str,
        assignment_type: str,
        assignment_id: str,
        shift_id: str,
        location_id: str,
        start_datetime: datetime,
        end_datetime: datetime,
    ) -> None:
        if assignment_type not in VALID_ASSIGNMENT_TYPES:
            raise ValueError(
                f"assignment_type must be one of {set(VALID_ASSIGNMENT_TYPES)}, "
                f"got {assignment_type!r}."
            )
        if start_datetime >= end_datetime:
            raise ValueError(
                f"start_datetime ({start_datetime}) must be strictly before "
                f"end_datetime ({end_datetime})."
            )
        self.person_id: str = person_id
        self.assignment_type: str = assignment_type
        self.assignment_id: str = assignment_id
        self.shift_id: str = shift_id
        self.location_id: str = location_id
        self.start_datetime: datetime = start_datetime
        self.end_datetime: datetime = end_datetime

    def overlaps(self, other: Assignment) -> bool:
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
            f"Assignment("
            f"person_id={self.person_id!r}, "
            f"type={self.assignment_type!r}, "
            f"assignment_id={self.assignment_id!r}, "
            f"shift_id={self.shift_id!r}, "
            f"location_id={self.location_id!r}, "
            f"start={self.start_datetime!r}, "
            f"end={self.end_datetime!r})"
        )
