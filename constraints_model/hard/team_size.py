from __future__ import annotations

from collections import defaultdict

from core.schedule.assignment import Assignment


def validate_team_size(
    assignments: list[Assignment],
    task_team_size: dict[str, tuple[int, int]],
) -> None:
    """Enforce the hard constraint that each task is staffed within its allowed headcount range.

    Groups task assignments by (task_id, start_datetime, end_datetime) to identify
    concurrent execution slots, then validates that the number of people assigned
    to each slot falls within the configured minimum and maximum. Tasks without a
    configuration entry are not checked.

    Args:
        assignments:     List of assignments to validate.
        task_team_size:  Maps task_id → (min_people, max_people) inclusive range.
    """
    # slot_counts[(task_id, start, end)] -> set of person_ids
    slot_persons: dict[tuple, set[str]] = defaultdict(set)

    for a in assignments:
        if a.assignment_type != "task":
            continue
        key = (a.assignment_id, a.start_datetime, a.end_datetime)
        slot_persons[key].add(a.person_id)

    for (task_id, start, end), persons in slot_persons.items():
        limits = task_team_size.get(task_id)
        if limits is None:
            continue

        min_people, max_people = limits
        count = len(persons)

        if not (min_people <= count <= max_people):
            raise ValueError(
                f"Task {task_id!r} ({start}–{end}) has {count} person(s) assigned, "
                f"but requires between {min_people} and {max_people}."
            )
