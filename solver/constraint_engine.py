from __future__ import annotations

from core.schedule.assignment import Assignment

from constraints_model.hard.person_overlap import validate_person_overlap
from constraints_model.hard.skill_matching import validate_skill_matching
from constraints_model.hard.resource_exclusivity import validate_resource_exclusivity_constraint
from constraints_model.hard.availability import validate_availability
from constraints_model.hard.max_working_hours import validate_max_working_hours
from constraints_model.hard.minimum_rest import validate_minimum_rest
from constraints_model.hard.travel_time import validate_travel_time_constraint
from constraints_model.hard.task_dependencies import validate_task_dependencies
from constraints_model.hard.team_size import validate_team_size


class ConstraintEngine:
    """Aggregates all hard constraints into a single validation entry point.

    The solver calls this engine once per candidate schedule rather than
    invoking individual constraints directly. Each hard constraint is executed
    sequentially. The first violation encountered raises a ValueError which
    propagates to the caller unchanged. Contains no solver logic or scoring.
    """

    def validate(
        self,
        assignments: list[Assignment],
        context: dict,
    ) -> None:
        """Run all hard constraints against the given assignments.

        Context keys used (all optional — constraints skip gracefully if absent):

            resource_assignments    list[ResourceAssignment]
            person_skills           dict[str, set[str]]
            skill_hierarchy         dict[str, set[str]]
            required_skills         dict[str, set[str]]
            person_availability     dict[str, list[tuple[datetime, datetime]]]
            max_hours_per_day       dict[str, float]
            max_hours_per_period    dict[str, float]
            minimum_rest_minutes    dict[str, int]
            travel_matrix           TravelTimeMatrix
            task_dependencies       dict[str, set[str]]
            task_team_size          dict[str, tuple[int, int]]

        Raises ValueError on the first constraint violation found.
        """
        validate_person_overlap(assignments)

        validate_skill_matching(
            assignments,
            person_skills=context.get("person_skills", {}),
            skill_hierarchy=context.get("skill_hierarchy", {}),
            required_skills=context.get("required_skills", {}),
        )

        validate_resource_exclusivity_constraint(
            context.get("resource_assignments", []),
        )

        validate_availability(
            assignments,
            person_availability=context.get("person_availability", {}),
        )

        validate_max_working_hours(
            assignments,
            max_hours_per_day=context.get("max_hours_per_day", {}),
            max_hours_per_period=context.get("max_hours_per_period", {}),
        )

        validate_minimum_rest(
            assignments,
            minimum_rest_minutes=context.get("minimum_rest_minutes", {}),
        )

        if context.get("travel_matrix") is not None:
            validate_travel_time_constraint(
                assignments,
                travel_matrix=context["travel_matrix"],
            )

        validate_task_dependencies(
            assignments,
            task_dependencies=context.get("task_dependencies", {}),
        )

        validate_team_size(
            assignments,
            task_team_size=context.get("task_team_size", {}),
        )
