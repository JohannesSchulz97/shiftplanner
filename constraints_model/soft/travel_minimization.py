from __future__ import annotations

from core.schedule.assignment import Assignment
from core.locations.travel_time_matrix import TravelTimeMatrix


def compute_travel_penalty(
    assignments: list[Assignment],
    travel_matrix: TravelTimeMatrix,
) -> float:
    """Compute a penalty proportional to total travel time between consecutive assignments.

    Schedules that require more travel between locations accumulate higher penalties,
    encouraging the solver to prefer locality when assigning consecutive shifts.
    Same-location transitions contribute zero penalty. Only defined travel pairs
    in the matrix are scored — undefined pairs are silently skipped.

    Higher penalty = more total travel = worse schedule quality.

    Args:
        assignments:    List of assignments in the schedule.
        travel_matrix:  Matrix of travel durations between location pairs in minutes.

    Returns:
        Total travel minutes as a float penalty.
    """
    by_person: dict[str, list[Assignment]] = {}
    for a in assignments:
        by_person.setdefault(a.person_id, []).append(a)

    penalty = 0.0

    for group in by_person.values():
        sorted_group = sorted(group, key=lambda a: a.start_datetime)

        for prev, nxt in zip(sorted_group, sorted_group[1:]):
            if prev.location_id == nxt.location_id:
                continue
            try:
                penalty += travel_matrix.get_travel_minutes(
                    prev.location_id,
                    nxt.location_id,
                )
            except ValueError:
                pass

    return penalty
