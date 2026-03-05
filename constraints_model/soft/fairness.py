from __future__ import annotations

from collections import defaultdict
from statistics import variance

from core.schedule.assignment import Assignment


def compute_fairness_penalty(
    assignments: list[Assignment],
    offered_time_minutes: dict[str, int],
) -> float:
    """Compute a penalty measuring imbalance in how offered time is converted to assignments.

    Fairness is defined as equal distribution of assigned work relative to each
    person's voluntarily offered availability. The penalty is the statistical
    variance of conversion ratios across all eligible people.

    A penalty of zero means all persons had the same proportion of their offered
    time assigned. Only persons with offered time > 0 are included.
    Expected availability is explicitly excluded — only offered time is considered.

    Higher penalty = greater unfairness.

    Args:
        assignments:           List of assignments in the schedule.
        offered_time_minutes:  Maps person_id → total offered minutes (> 0 to be included).

    Returns:
        Variance of conversion ratios as a float. Returns 0.0 if fewer than 2
        eligible persons exist.
    """
    assigned_minutes: dict[str, float] = defaultdict(float)
    for a in assignments:
        duration = (a.end_datetime - a.start_datetime).total_seconds() / 60
        assigned_minutes[a.person_id] += duration

    conversion_ratios = [
        assigned_minutes[person_id] / offered
        for person_id, offered in offered_time_minutes.items()
        if offered > 0
    ]

    if len(conversion_ratios) < 2:
        return 0.0

    return variance(conversion_ratios)
