from __future__ import annotations

from core.schedule.assignment import Assignment


def validate_task_dependencies(
    assignments: list[Assignment],
    task_dependencies: dict[str, set[str]],
) -> None:
    """Enforce the hard constraint that dependent tasks are scheduled after their prerequisites.

    For each task with declared dependencies, every assignment of that task must
    start only after all assignments of each prerequisite task have ended.
    Coverage assignments are ignored — only task assignments are evaluated.

    Args:
        assignments:        List of assignments to validate.
        task_dependencies:  Maps task_id → set of prerequisite task_ids that
                            must fully complete before the dependent task begins.
    """
    task_assignments: dict[str, list[Assignment]] = {}
    for a in assignments:
        if a.assignment_type == "task":
            task_assignments.setdefault(a.assignment_id, []).append(a)

    for task_id, prerequisites in task_dependencies.items():
        dependent_assignments = task_assignments.get(task_id, [])
        if not dependent_assignments:
            continue

        for prereq_id in prerequisites:
            prereq_assignments = task_assignments.get(prereq_id, [])
            if not prereq_assignments:
                continue

            prereq_latest_end = max(a.end_datetime for a in prereq_assignments)

            for dep in dependent_assignments:
                if dep.start_datetime < prereq_latest_end:
                    raise ValueError(
                        f"Task {task_id!r} starts before prerequisite {prereq_id!r} has finished: "
                        f"dependent starts at {dep.start_datetime}, "
                        f"but prerequisite last ends at {prereq_latest_end}."
                    )
