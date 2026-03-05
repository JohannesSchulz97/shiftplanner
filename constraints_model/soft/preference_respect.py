from __future__ import annotations

from datetime import datetime

from core.schedule.assignment import Assignment


def compute_preference_penalty(
    assignments: list[Assignment],
    preferred_windows: dict[str, list[tuple[datetime, datetime]]],
) -> float:
    """Compute a penalty for assignments that fall outside a person's preferred windows.

    Encourages schedules aligned with personal preferences without making them
    mandatory. An assignment outside all preferred windows contributes its full
    duration in minutes as penalty. Persons with no declared preferences are
    not penalised.

    Higher penalty = more preference violations = worse schedule quality.

    Args:
        assignments:        List of assignments in the schedule.
        preferred_windows:  Maps person_id → list of (window_start, window_end) tuples
                            representing preferred working periods.

    Returns:
        Total penalty in minutes as a float.
    """
    penalty = 0.0

    for a in assignments:
        windows = preferred_windows.get(a.person_id)
        if not windows:
            continue

        within_preference = any(
            window_start <= a.start_datetime and a.end_datetime <= window_end
            for window_start, window_end in windows
        )

        if not within_preference:
            duration_minutes = (
                a.end_datetime - a.start_datetime
            ).total_seconds() / 60
            penalty += duration_minutes

    return penalty
