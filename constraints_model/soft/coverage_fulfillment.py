from __future__ import annotations

from collections import defaultdict

from core.schedule.assignment import Assignment


def compute_coverage_penalty(
    assignments: list[Assignment],
    coverage_requirements: list[tuple[str, int]],
) -> float:
    """Compute a penalty proportional to unmet coverage staffing requirements.

    Each coverage requirement specifies how many people must be assigned to a
    coverage slot. Any shortfall contributes one penalty unit per missing person.
    A penalty of zero means all coverage requirements are fully met.
    The solver should minimise this value to maximise coverage fulfillment.

    Higher penalty = more uncovered staffing need.

    Args:
        assignments:           List of assignments in the schedule.
        coverage_requirements: List of (coverage_id, required_count) pairs.

    Returns:
        Total penalty as a float.
    """
    assigned_counts: dict[str, int] = defaultdict(int)
    for a in assignments:
        if a.assignment_type == "coverage":
            assigned_counts[a.assignment_id] += 1

    penalty = 0.0
    for coverage_id, required_count in coverage_requirements:
        assigned = assigned_counts[coverage_id]
        penalty += max(0, required_count - assigned)

    return penalty
