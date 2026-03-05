from __future__ import annotations

from datetime import datetime

from core.schedule.assignment import Assignment


def validate_availability(
    assignments: list[Assignment],
    person_availability: dict[str, list[tuple[datetime, datetime]]],
) -> None:
    """Enforce the hard constraint that assignments fall within declared availability windows.

    For each assignment, the person's full time window must be contained within
    at least one of their allowed working windows. An assignment that extends
    beyond or outside all available windows is rejected.

    Args:
        assignments:          List of assignments to validate.
        person_availability:  Maps person_id → list of (window_start, window_end) tuples
                              representing allowed working periods.
    """
    for assignment in assignments:
        person_id = assignment.person_id
        windows = person_availability.get(person_id, [])

        contained = any(
            window_start <= assignment.start_datetime
            and assignment.end_datetime <= window_end
            for window_start, window_end in windows
        )

        if not contained:
            raise ValueError(
                f"Person {person_id!r} is not available for assignment "
                f"{assignment.assignment_id!r} "
                f"({assignment.start_datetime}–{assignment.end_datetime}): "
                f"no declared availability window covers this period."
            )
