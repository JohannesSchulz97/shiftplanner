from __future__ import annotations

from core.schedule.schedule import Schedule
from core.schedule.resource_assignment import validate_resource_exclusivity


class ScheduleValidator:
    """Enforces conflict-free guarantees on a Schedule before it is accepted as valid.

    Validates hard constraints — person overlap and resource exclusivity.
    Does not generate, modify, or interpret schedules.
    Raises ValueError on the first violation found within each check.
    """

    def validate(self, schedule: Schedule) -> None:
        """Run all hard-constraint validations against the given schedule.

        Raises ValueError if any constraint is violated.
        """
        self._validate_person_overlap(schedule)
        validate_resource_exclusivity(schedule.resource_assignments)

    def _validate_person_overlap(self, schedule: Schedule) -> None:
        """Raise ValueError if any person has two overlapping assignments."""
        by_person: dict[str, list] = {}
        for a in schedule.assignments:
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
