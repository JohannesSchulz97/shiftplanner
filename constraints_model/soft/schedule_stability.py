from __future__ import annotations

from core.schedule.assignment import Assignment


def _to_tuple(a: Assignment) -> tuple:
    return (
        a.person_id,
        a.assignment_id,
        a.start_datetime,
        a.end_datetime,
        a.location_id,
    )


def compute_schedule_stability_penalty(
    previous_assignments: list[Assignment],
    new_assignments: list[Assignment],
) -> float:
    """Compute a penalty measuring disruption between a previous and a new schedule.

    Penalises any deviation from a previously published schedule to minimise
    unnecessary changes during re-solving. Each removed or added assignment
    contributes equally to the penalty, regardless of how significant the change is.

    A penalty of zero means the new schedule is identical to the previous one.
    Higher penalty = more disruption.

    Args:
        previous_assignments: Assignments from the previously published schedule.
        new_assignments:      Assignments from the newly generated schedule.

    Returns:
        Total disruption penalty as a float.
    """
    previous_set = {_to_tuple(a) for a in previous_assignments}
    new_set = {_to_tuple(a) for a in new_assignments}

    removed = previous_set - new_set
    added = new_set - previous_set

    return float(len(removed) + len(added))
