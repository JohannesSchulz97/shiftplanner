from __future__ import annotations

from core.schedule.assignment import Assignment


def compute_task_priority_penalty(
    assignments: list[Assignment],
    required_tasks: set[str],
    optional_tasks: set[str],
) -> float:
    """Compute a penalty score reflecting unmet required tasks alongside optional work.

    Required tasks take precedence over optional ones. If any required task has
    no assignments, each optional assignment scheduled in its place contributes
    to the penalty. A penalty of zero means all required tasks are satisfied.

    Higher penalty = worse schedule quality.

    Args:
        assignments:     List of task assignments in the schedule.
        required_tasks:  Set of task_ids that must be fully assigned.
        optional_tasks:  Set of task_ids that are desirable but not mandatory.

    Returns:
        Penalty as a float. Zero if all required tasks have at least one assignment.
    """
    assigned_task_ids = {
        a.assignment_id
        for a in assignments
        if a.assignment_type == "task"
    }

    unsatisfied_required = required_tasks - assigned_task_ids

    if not unsatisfied_required:
        return 0.0

    optional_assignment_count = sum(
        1 for a in assignments
        if a.assignment_type == "task" and a.assignment_id in optional_tasks
    )

    return float(optional_assignment_count)
