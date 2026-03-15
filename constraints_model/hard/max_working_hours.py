from __future__ import annotations

from collections import defaultdict

from core.schedule.assignment import Assignment


def validate_max_working_hours(
    assignments: list[Assignment],
    max_hours_per_day: dict[str, float],
    max_hours_per_period: dict[str, float],
) -> None:
    """Enforce the hard constraint that persons do not exceed maximum working hours.

    Validates two limits per person:
    - daily total: hours assigned on any single calendar day
    - period total: hours assigned across the entire planning period

    Limits are legal or contractual upper bounds. Raises ValueError on the
    first violation found.

    Args:
        assignments:          List of assignments to validate.
        max_hours_per_day:    Maps person_id → maximum allowed hours per calendar day.
        max_hours_per_period: Maps person_id → maximum allowed hours per planning period.
    """
    # hours_per_day[person_id][date] -> total hours
    hours_per_day: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    # hours_per_period[person_id] -> total hours
    hours_per_period: dict[str, float] = defaultdict(float)

    for assignment in assignments:
        person_id = assignment.person_id
        duration_hours = (
            assignment.end_datetime - assignment.start_datetime
        ).total_seconds() / 3600

        day = assignment.start_datetime.date()
        hours_per_day[person_id][day] += duration_hours
        hours_per_period[person_id] += duration_hours

    for person_id, daily_totals in hours_per_day.items():
        limit = max_hours_per_day.get(person_id)
        if limit is None:
            continue
        for day, total in daily_totals.items():
            if total > limit:
                raise ValueError(
                    f"Person {person_id!r} exceeds daily working hours on {day}: "
                    f"assigned {total:.2f}h, limit is {limit:.2f}h."
                )

    for person_id, total in hours_per_period.items():
        limit = max_hours_per_period.get(person_id)
        if limit is None:
            continue
        if total > limit:
            raise ValueError(
                f"Person {person_id!r} exceeds planning-period working hours: "
                f"assigned {total:.2f}h, limit is {limit:.2f}h."
            )
