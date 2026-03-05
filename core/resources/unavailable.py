from __future__ import annotations
from datetime import datetime


class ResourceUnavailability:
    """An explicit time window during which a resource cannot be used.

    Resources are unavailable only when explicitly marked for a time window.
    Any window not covered by an instance of this class is considered available
    by default.
    """

    def __init__(
        self,
        resource_id: str,
        start_datetime: datetime,
        end_datetime: datetime,
        reason: str | None = None,
    ) -> None:
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise ValueError("resource_id must be a non-empty string.")
        if start_datetime >= end_datetime:
            raise ValueError(
                f"start_datetime ({start_datetime}) must be strictly before "
                f"end_datetime ({end_datetime})."
            )
        self.resource_id: str = resource_id.strip()
        self.start_datetime: datetime = start_datetime
        self.end_datetime: datetime = end_datetime
        self.reason: str | None = reason

    def overlaps(self, start_datetime: datetime, end_datetime: datetime) -> bool:
        """Return True if the given interval overlaps this unavailability window.

        Two intervals overlap if:
            requested_start < stored_end AND requested_end > stored_start
        Adjacent intervals (end == start) do NOT overlap.
        """
        return start_datetime < self.end_datetime and end_datetime > self.start_datetime

    def __repr__(self) -> str:
        return (
            f"ResourceUnavailability("
            f"resource_id={self.resource_id!r}, "
            f"start={self.start_datetime!r}, "
            f"end={self.end_datetime!r}, "
            f"reason={self.reason!r})"
        )
