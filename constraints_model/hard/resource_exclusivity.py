from __future__ import annotations

from core.schedule.resource_assignment import ResourceAssignment


def validate_resource_exclusivity_constraint(
    resource_assignments: list[ResourceAssignment],
) -> None:
    """Enforce the hard constraint that shared resources are used by at most one person at a time.

    Groups resource assignments by resource_id and checks each group pairwise
    for overlapping time windows. Raises ValueError on the first conflict found.
    """
    by_resource: dict[str, list[ResourceAssignment]] = {}
    for a in resource_assignments:
        by_resource.setdefault(a.resource_id, []).append(a)

    for resource_id, group in by_resource.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a.overlaps(b):
                    raise ValueError(
                        f"Resource {resource_id!r} is assigned to multiple people "
                        f"during overlapping windows: "
                        f"{a.person_id!r} ({a.start_datetime}–{a.end_datetime}) "
                        f"conflicts with "
                        f"{b.person_id!r} ({b.start_datetime}–{b.end_datetime})."
                    )
