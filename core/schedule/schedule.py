from __future__ import annotations

from core.schedule.assignment import Assignment
from core.schedule.resource_assignment import ResourceAssignment


class Schedule:
    """Output structure produced by the solver representing a planned schedule.

    A Schedule is a pure data container of assignments and resource assignments.
    It does not validate correctness, check overlaps, or enforce any constraints.
    The solver is the sole authority on producing a conflict-free plan.
    """

    def __init__(
        self,
        assignments: list[Assignment] | None = None,
        resource_assignments: list[ResourceAssignment] | None = None,
        version: str | None = None,
    ) -> None:
        self.assignments: list[Assignment] = assignments if assignments is not None else []
        self.resource_assignments: list[ResourceAssignment] = (
            resource_assignments if resource_assignments is not None else []
        )
        self.version: str | None = version

    def add_assignment(self, assignment: Assignment) -> None:
        """Append a person assignment to the schedule."""
        self.assignments.append(assignment)

    def add_resource_assignment(self, resource_assignment: ResourceAssignment) -> None:
        """Append a resource assignment to the schedule."""
        self.resource_assignments.append(resource_assignment)

    def get_assignments_for_person(self, person_id: str) -> list[Assignment]:
        """Return all assignments for the given person."""
        return [a for a in self.assignments if a.person_id == person_id]

    def get_resource_assignments(self, resource_id: str) -> list[ResourceAssignment]:
        """Return all resource assignments for the given resource."""
        return [r for r in self.resource_assignments if r.resource_id == resource_id]

    def __repr__(self) -> str:
        return (
            f"Schedule("
            f"assignments={len(self.assignments)}, "
            f"resource_assignments={len(self.resource_assignments)}, "
            f"version={self.version!r})"
        )
