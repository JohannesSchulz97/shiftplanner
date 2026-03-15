from __future__ import annotations

from core.schedule.assignment import Assignment

from constraints_model.soft.task_priority import compute_task_priority_penalty
from constraints_model.soft.coverage_fulfillment import compute_coverage_penalty
from constraints_model.soft.fairness import compute_fairness_penalty
from constraints_model.soft.travel_minimization import compute_travel_penalty
from constraints_model.soft.preference_respect import compute_preference_penalty
from constraints_model.soft.schedule_stability import compute_schedule_stability_penalty


class ScoringEngine:
    """Evaluates schedule quality by aggregating all soft constraint penalties.

    Produces a total penalty score and a per-constraint breakdown. Lower scores
    indicate better schedules. Contains no validation or solver logic — it only
    measures quality of an already-generated candidate schedule.
    """

    def score(
        self,
        assignments: list[Assignment],
        context: dict,
    ) -> tuple[float, dict[str, float]]:
        """Compute the total soft-constraint penalty for the given assignments.

        Context keys used (all optional — scores default to 0.0 if absent):

            required_tasks          set[str]
            optional_tasks          set[str]
            coverage_requirements   list[tuple[str, int]]
            offered_time_minutes    dict[str, int]
            travel_matrix           TravelTimeMatrix
            preferred_windows       dict[str, list[tuple[datetime, datetime]]]
            previous_assignments    list[Assignment]

        Returns:
            A tuple of (total_score, breakdown) where breakdown maps each
            soft constraint name to its individual penalty value.
        """
        breakdown: dict[str, float] = {}

        breakdown["task_priority"] = compute_task_priority_penalty(
            assignments,
            required_tasks=context.get("required_tasks", set()),
            optional_tasks=context.get("optional_tasks", set()),
        )

        breakdown["coverage"] = compute_coverage_penalty(
            assignments,
            coverage_requirements=context.get("coverage_requirements", []),
        )

        breakdown["fairness"] = compute_fairness_penalty(
            assignments,
            offered_time_minutes=context.get("offered_time_minutes", {}),
        )

        if context.get("travel_matrix") is not None:
            breakdown["travel"] = compute_travel_penalty(
                assignments,
                travel_matrix=context["travel_matrix"],
            )
        else:
            breakdown["travel"] = 0.0

        breakdown["preference"] = compute_preference_penalty(
            assignments,
            preferred_windows=context.get("preferred_windows", {}),
        )

        breakdown["stability"] = compute_schedule_stability_penalty(
            previous_assignments=context.get("previous_assignments", []),
            new_assignments=assignments,
        )

        total_score = sum(breakdown.values())
        return total_score, breakdown
