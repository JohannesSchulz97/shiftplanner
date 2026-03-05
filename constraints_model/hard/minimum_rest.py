from __future__ import annotations

from core.schedule.assignment import Assignment


def validate_minimum_rest(
    assignments: list[Assignment],
    minimum_rest_minutes: dict[str, int],
) -> None:
    """Enforce the hard constraint that persons have sufficient rest between assignments.

    Guarantees a minimum recovery gap between the end of one assignment and the
    start of the next for the same person. Persons without a configured rest
    requirement are not checked. Raises ValueError on the first violation found.

    Args:
        assignments:            List of assignments to validate.
        minimum_rest_minutes:   Maps person_id → required rest gap in minutes.
    """
    by_person: dict[str, list[Assignment]] = {}
    for a in assignments:
        by_person.setdefault(a.person_id, []).append(a)

    for person_id, group in by_person.items():
        required = minimum_rest_minutes.get(person_id)
        if required is None:
            continue

        sorted_group = sorted(group, key=lambda a: a.start_datetime)

        for prev, nxt in zip(sorted_group, sorted_group[1:]):
            gap_minutes = (
                nxt.start_datetime - prev.end_datetime
            ).total_seconds() / 60

            if gap_minutes < required:
                raise ValueError(
                    f"Person {person_id!r} has insufficient rest between assignments: "
                    f"requires {required} min, got {gap_minutes:.1f} min. "
                    f"Previous: {prev.assignment_id!r} (ends {prev.end_datetime}), "
                    f"next: {nxt.assignment_id!r} (starts {nxt.start_datetime})."
                )
