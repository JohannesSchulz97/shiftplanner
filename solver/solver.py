from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from ortools.sat.python import cp_model

from core.schedule.assignment import Assignment
from solver.solver_context import SolverContext
from solver.constraint_engine import ConstraintEngine
from solver.scoring_engine import ScoringEngine
from solver.infeasibility_report import InfeasibilityReport
from solver.cp_sat_adapter import CpSatAdapter

_FEASIBLE_STATUSES = (cp_model.OPTIMAL, cp_model.FEASIBLE)
_COVERAGE_WEIGHT = 1000
_FAIRNESS_WEIGHT = 10
_RATIO_SCALE = 1000  # fixed-point scale for offered-time ratios


def _has_skill(skill: str, person_skills: set[str], hierarchy: dict[str, set[str]]) -> bool:
    """Return True if person holds the skill directly or via a higher skill in the hierarchy."""
    if skill in person_skills:
        return True
    return any(skill in hierarchy.get(held, set()) for held in person_skills)


def _shift_available(
    shift_start: datetime,
    shift_end: datetime,
    windows: list[tuple[datetime, datetime]],
) -> bool:
    """Return True if the shift is fully contained within at least one availability window."""
    return any(w_start <= shift_start and shift_end <= w_end for w_start, w_end in windows)


def _shifts_overlap(m1: dict, m2: dict) -> bool:
    return m1["start_datetime"] < m2["end_datetime"] and m1["end_datetime"] > m2["start_datetime"]


class Solver:
    """CP-SAT-backed schedule solver.

    Encodes hard constraints directly into the CP-SAT model and expresses
    soft constraints as weighted penalty terms in the objective. After solving,
    the CP-SAT solution is decoded into Assignment objects and post-scored
    through the ScoringEngine for a consistent breakdown.

    constraint_context keys consumed:
        shift_metadata      dict[str, dict]  — per-shift: assignment_type,
                            assignment_id, location_id, start_datetime, end_datetime
        person_skills       dict[str, set[str]]
        skill_hierarchy     dict[str, set[str]]
        required_skills     dict[str, set[str]]   (keyed by assignment_id)
        person_availability dict[str, list[tuple[datetime, datetime]]]
        max_hours_per_day   dict[str, float]
        minimum_rest_minutes dict[str, int]

    scoring_context keys consumed:
        coverage_requirements  list[tuple[str, int]]  (coverage_id, required_count)
        offered_time_minutes   dict[str, int]
        (all other keys forwarded to ScoringEngine unchanged)
    """

    def __init__(
        self,
        constraint_engine: ConstraintEngine,
        scoring_engine: ScoringEngine,
    ) -> None:
        self._constraint_engine = constraint_engine
        self._scoring_engine = scoring_engine

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_initial(
        self,
        context: SolverContext,
        constraint_context: dict,
        scoring_context: dict,
    ) -> tuple[list[Assignment] | None, dict | None]:
        """Generate a schedule using CP-SAT and return the best feasible solution.

        Returns:
            (assignments, result) on success, or (None, infeasibility_report) on failure.
        """
        adapter = CpSatAdapter()
        model = adapter.model

        shift_meta: dict[str, dict] = constraint_context.get("shift_metadata", {})
        valid_shifts = [s for s in context.shift_ids if s in shift_meta]
        people = context.people_ids

        if not valid_shifts or not people:
            report = InfeasibilityReport()
            report.add_failure("setup", "No valid shifts or people in context.")
            return None, report.to_dict()

        # ------------------------------------------------------------------
        # Decision variables  x[person_id][shift_id] ∈ {0, 1}
        # ------------------------------------------------------------------
        x: dict[str, dict[str, cp_model.IntVar]] = {}
        for person_id in people:
            x[person_id] = {}
            for shift_id in valid_shifts:
                meta = shift_meta[shift_id]
                x[person_id][shift_id] = adapter.create_assignment_var(
                    person_id,
                    meta.get("assignment_id", shift_id),
                    shift_id,
                )

        # ------------------------------------------------------------------
        # Hard constraint 1 — Availability
        # ------------------------------------------------------------------
        person_availability: dict = constraint_context.get("person_availability", {})
        for person_id in people:
            windows = person_availability.get(person_id, [])
            for shift_id in valid_shifts:
                meta = shift_meta[shift_id]
                if not _shift_available(meta["start_datetime"], meta["end_datetime"], windows):
                    model.Add(x[person_id][shift_id] == 0)

        # ------------------------------------------------------------------
        # Hard constraint 2 — Skill matching (with hierarchy)
        # ------------------------------------------------------------------
        person_skills: dict = constraint_context.get("person_skills", {})
        skill_hierarchy: dict = constraint_context.get("skill_hierarchy", {})
        required_skills: dict = constraint_context.get("required_skills", {})
        for person_id in people:
            skills = person_skills.get(person_id, set())
            for shift_id in valid_shifts:
                assignment_id = shift_meta[shift_id].get("assignment_id", shift_id)
                needed = required_skills.get(assignment_id, set())
                if any(not _has_skill(s, skills, skill_hierarchy) for s in needed):
                    model.Add(x[person_id][shift_id] == 0)

        # ------------------------------------------------------------------
        # Hard constraint 3 — No person overlap (pairwise shift exclusion)
        # ------------------------------------------------------------------
        for person_id in people:
            for i, s1 in enumerate(valid_shifts):
                for s2 in valid_shifts[i + 1:]:
                    if _shifts_overlap(shift_meta[s1], shift_meta[s2]):
                        model.Add(x[person_id][s1] + x[person_id][s2] <= 1)

        # ------------------------------------------------------------------
        # Hard constraint 4 — Max working hours per day
        # ------------------------------------------------------------------
        max_hours_per_day: dict = constraint_context.get("max_hours_per_day", {})
        shifts_by_day: dict[object, list[str]] = defaultdict(list)
        for shift_id in valid_shifts:
            shifts_by_day[shift_meta[shift_id]["start_datetime"].date()].append(shift_id)

        for person_id in people:
            limit = max_hours_per_day.get(person_id)
            if limit is None:
                continue
            limit_minutes = int(limit * 60)
            for day_shifts in shifts_by_day.values():
                terms = [
                    int((shift_meta[s]["end_datetime"] - shift_meta[s]["start_datetime"])
                        .total_seconds() / 60) * x[person_id][s]
                    for s in day_shifts
                ]
                model.Add(sum(terms) <= limit_minutes)

        # ------------------------------------------------------------------
        # Hard constraint 5 — Minimum rest between consecutive shifts
        # ------------------------------------------------------------------
        minimum_rest: dict = constraint_context.get("minimum_rest_minutes", {})
        for person_id in people:
            rest_required = minimum_rest.get(person_id)
            if rest_required is None:
                continue
            for i, s1 in enumerate(valid_shifts):
                m1 = shift_meta[s1]
                for s2 in valid_shifts[i + 1:]:
                    m2 = shift_meta[s2]
                    # Only check pairs where one ends before the other starts
                    gap: float
                    if m1["end_datetime"] <= m2["start_datetime"]:
                        gap = (m2["start_datetime"] - m1["end_datetime"]).total_seconds() / 60
                        if 0 <= gap < rest_required:
                            model.Add(x[person_id][s1] + x[person_id][s2] <= 1)
                    elif m2["end_datetime"] <= m1["start_datetime"]:
                        gap = (m1["start_datetime"] - m2["end_datetime"]).total_seconds() / 60
                        if 0 <= gap < rest_required:
                            model.Add(x[person_id][s1] + x[person_id][s2] <= 1)

        # ------------------------------------------------------------------
        # Objective — soft penalties
        # ------------------------------------------------------------------
        objective_terms: list = []

        # Soft 1: Coverage deficit (weight 1000)
        coverage_requirements: list[tuple[str, int]] = scoring_context.get(
            "coverage_requirements", []
        )
        for cov_id, required_count in coverage_requirements:
            if cov_id not in valid_shifts:
                continue
            deficit = model.NewIntVar(0, len(people), f"deficit__{cov_id}")
            assigned_sum = sum(x[p][cov_id] for p in people)
            model.Add(deficit >= required_count - assigned_sum)
            model.Add(deficit >= 0)
            objective_terms.append(_COVERAGE_WEIGHT * deficit)

        # Soft 2: Fairness — equalize offered-time conversion ratios (weight 10)
        offered_time: dict[str, int] = scoring_context.get("offered_time_minutes", {})
        ratio_vars: list[cp_model.IntVar] = []
        for person_id in people:
            offered = offered_time.get(person_id, 0)
            if offered <= 0:
                continue
            duration_terms = [
                int((shift_meta[s]["end_datetime"] - shift_meta[s]["start_datetime"])
                    .total_seconds() / 60) * x[person_id][s]
                for s in valid_shifts
            ]
            total_assigned = model.NewIntVar(0, 24 * 60, f"total_assigned__{person_id}")
            model.Add(total_assigned == sum(duration_terms))

            # ratio_var ≈ assigned_minutes * SCALE / offered  (integer division)
            total_scaled = model.NewIntVar(0, 24 * 60 * _RATIO_SCALE, f"total_scaled__{person_id}")
            model.Add(total_scaled == total_assigned * _RATIO_SCALE)
            ratio_var = model.NewIntVar(0, _RATIO_SCALE, f"ratio__{person_id}")
            model.AddDivisionEquality(ratio_var, total_scaled, offered)
            ratio_vars.append(ratio_var)

        if len(ratio_vars) >= 2:
            max_ratio = model.NewIntVar(0, _RATIO_SCALE, "max_ratio")
            min_ratio = model.NewIntVar(0, _RATIO_SCALE, "min_ratio")
            for rv in ratio_vars:
                model.Add(max_ratio >= rv)
                model.Add(min_ratio <= rv)
            objective_terms.append(_FAIRNESS_WEIGHT * (max_ratio - min_ratio))

        if objective_terms:
            model.Minimize(sum(objective_terms))

        # ------------------------------------------------------------------
        # Solve
        # ------------------------------------------------------------------
        status = adapter.solve()

        if status not in _FEASIBLE_STATUSES:
            report = InfeasibilityReport()
            report.add_failure(
                "cp_sat",
                f"CP-SAT returned status: {adapter.solver.StatusName(status)}.",
            )
            return None, report.to_dict()

        # ------------------------------------------------------------------
        # Decode solution → Assignment objects
        # ------------------------------------------------------------------
        assignments: list[Assignment] = []
        for person_id in people:
            for shift_id in valid_shifts:
                if adapter.get_value(x[person_id][shift_id]) == 1:
                    meta = shift_meta[shift_id]
                    assignments.append(Assignment(
                        person_id=person_id,
                        assignment_type=meta.get("assignment_type", "coverage"),
                        assignment_id=meta.get("assignment_id", shift_id),
                        shift_id=shift_id,
                        location_id=meta.get("location_id", ""),
                        start_datetime=meta["start_datetime"],
                        end_datetime=meta["end_datetime"],
                    ))

        total, breakdown = self._scoring_engine.score(assignments, scoring_context)
        return assignments, {"score": total, "breakdown": breakdown}
