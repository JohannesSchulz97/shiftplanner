from __future__ import annotations

from core.schedule.assignment import Assignment
from core.locations.travel_time_matrix import TravelTimeMatrix
from core.locations.travel_validator import TravelValidator


def validate_travel_time_constraint(
    assignments: list[Assignment],
    travel_matrix: TravelTimeMatrix,
) -> None:
    """Enforce the hard constraint that sufficient travel buffer exists between assignments.

    Delegates to TravelValidator to ensure consecutive assignments for the same
    person at different locations have enough gap to cover required travel time.
    Any ValueError raised by the validator is propagated unchanged.

    Args:
        assignments:    List of assignments to validate.
        travel_matrix:  Matrix of travel durations between location pairs.
    """
    TravelValidator().validate_travel_buffers(assignments, travel_matrix)
