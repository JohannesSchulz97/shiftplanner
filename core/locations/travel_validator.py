from __future__ import annotations

from core.schedule.assignment import Assignment
from core.locations.travel_time_matrix import TravelTimeMatrix


class TravelValidator:
    """Ensures consecutive assignments respect the travel buffer between locations.

    Enforces the hard constraint that a person moving from one location to another
    must have sufficient gap between assignments to cover the required travel time.
    Does not modify schedules or generate assignments.
    """

    def validate_travel_buffers(
        self,
        assignments: list[Assignment],
        travel_matrix: TravelTimeMatrix,
    ) -> None:
        """Raise ValueError if any person cannot travel between consecutive assignments in time.

        Groups assignments by person, sorts by start time, and checks each consecutive
        pair at different locations for sufficient gap.
        """
        by_person: dict[str, list[Assignment]] = {}
        for a in assignments:
            by_person.setdefault(a.person_id, []).append(a)

        for person_id, group in by_person.items():
            sorted_group = sorted(group, key=lambda a: a.start_datetime)

            for prev, nxt in zip(sorted_group, sorted_group[1:]):
                if prev.location_id == nxt.location_id:
                    continue

                required_minutes = travel_matrix.get_travel_minutes(
                    prev.location_id,
                    nxt.location_id,
                )
                available_minutes = (
                    nxt.start_datetime - prev.end_datetime
                ).total_seconds() / 60

                if available_minutes < required_minutes:
                    raise ValueError(
                        f"Person {person_id!r} cannot travel from {prev.location_id!r} "
                        f"to {nxt.location_id!r} in time: "
                        f"requires {required_minutes} min, "
                        f"but only {available_minutes:.1f} min available "
                        f"({prev.end_datetime} → {nxt.start_datetime})."
                    )
