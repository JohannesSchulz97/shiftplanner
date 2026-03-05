from __future__ import annotations

from core.schedule.assignment import Assignment


def validate_person_overlap(assignments: list[Assignment]) -> None:
    """Enforce the hard constraint that no person has overlapping assignments.

    A person cannot be scheduled for two assignments whose time windows
    overlap. Assignments are grouped by person and checked pairwise using
    Assignment.overlaps(). Raises ValueError on the first conflict found.
    """
    by_person: dict[str, list[Assignment]] = {}
    for a in assignments:
        by_person.setdefault(a.person_id, []).append(a)

    for person_id, group in by_person.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a.overlaps(b):
                    raise ValueError(
                        f"Person {person_id!r} has overlapping assignments: "
                        f"{a.assignment_id!r} ({a.start_datetime}–{a.end_datetime}) "
                        f"conflicts with "
                        f"{b.assignment_id!r} ({b.start_datetime}–{b.end_datetime})."
                    )
