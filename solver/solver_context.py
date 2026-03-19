from __future__ import annotations

from typing import Optional

from core.schedule.assignment import Assignment
from core.locations.travel_time_matrix import TravelTimeMatrix


class SolverContext:
    """Aggregates all inputs required for schedule generation and refinement.

    SolverContext is a pure data container passed to the solver at the start
    of each solving run. It holds references to all domain entities and
    configuration the solver needs to produce or refine a schedule.
    It contains no solving, validation, or scoring logic.
    """

    def __init__(
        self,
        people_ids: list[str],
        tasks: list[str],
        coverage_requirements: list[str],
        shift_ids: list[str],
        existing_assignments: Optional[list[Assignment]] = None,
        travel_matrix: Optional[TravelTimeMatrix] = None,
    ) -> None:
        self.people_ids: list[str] = people_ids
        self.tasks: list[str] = tasks
        self.coverage_requirements: list[str] = coverage_requirements
        self.shift_ids: list[str] = shift_ids
        self.existing_assignments: Optional[list[Assignment]] = existing_assignments
        self.travel_matrix: Optional[TravelTimeMatrix] = travel_matrix

    def has_existing_schedule(self) -> bool:
        """Return True if a previously published schedule is present in context."""
        return (
            self.existing_assignments is not None
            and len(self.existing_assignments) > 0
        )

    def __repr__(self) -> str:
        return (
            f"SolverContext("
            f"people={len(self.people_ids)}, "
            f"tasks={len(self.tasks)}, "
            f"coverage_requirements={len(self.coverage_requirements)}, "
            f"shifts={len(self.shift_ids)}, "
            f"has_existing_schedule={self.has_existing_schedule()})"
        )
