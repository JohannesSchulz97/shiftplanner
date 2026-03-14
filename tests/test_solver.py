"""Integration tests for Solver soft constraints."""
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta

from solver.solver import Solver
from solver.solver_context import SolverContext
from solver.constraint_engine import ConstraintEngine
from solver.scoring_engine import ScoringEngine

BASE = datetime(2026, 3, 14)
SHIFT_START = BASE.replace(hour=9)
SHIFT_END = BASE.replace(hour=17)
SHIFT_MINUTES = int((SHIFT_END - SHIFT_START).total_seconds() / 60)  # 480


def _make_solver() -> Solver:
    return Solver(ConstraintEngine(), ScoringEngine())


def _build_shift_meta(shift_id: str) -> dict:
    return {
        shift_id: {
            "assignment_type": "coverage",
            "assignment_id": shift_id,
            "location_id": "loc1",
            "start_datetime": SHIFT_START,
            "end_datetime": SHIFT_END,
        }
    }


def _full_availability() -> list:
    """Availability window that fully covers the default shift."""
    return [(SHIFT_START - timedelta(hours=1), SHIFT_END + timedelta(hours=1))]


# ---------------------------------------------------------------------------
# test_fairness_two_people
# ---------------------------------------------------------------------------

def test_fairness_two_people():
    """Two people offer availability for the same shift; only 1 spot needed.

    The solver assigns at least one person and the fairness penalty is included
    in the scoring breakdown. With equal offered time the solver minimises the
    CP-SAT fairness term by equalising conversion ratios, but the penalty key
    must always be present and non-negative.
    """
    solver = _make_solver()
    shift_id = "s_fairness"

    context = SolverContext(
        people_ids=["alice", "bob"],
        tasks=[],
        coverage_requirements=[shift_id],
        shift_ids=[shift_id],
    )
    constraint_context = {
        "shift_metadata": _build_shift_meta(shift_id),
        "person_availability": {
            "alice": _full_availability(),
            "bob": _full_availability(),
        },
        "person_skills": {"alice": {"nurse"}, "bob": {"nurse"}},
        "skill_hierarchy": {},
        "required_skills": {shift_id: {"nurse"}},
    }
    scoring_context = {
        "coverage_requirements": [(shift_id, 1)],
        "offered_time_minutes": {"alice": SHIFT_MINUTES, "bob": SHIFT_MINUTES},
    }

    assignments, result = solver.generate_initial(context, constraint_context, scoring_context)

    assert assignments is not None, f"Solver returned infeasible: {result}"
    assert len(assignments) >= 1
    assert all(a.person_id in {"alice", "bob"} for a in assignments)
    assert "fairness" in result["breakdown"]
    assert result["breakdown"]["fairness"] >= 0.0


# ---------------------------------------------------------------------------
# test_coverage_fulfillment
# ---------------------------------------------------------------------------

def test_coverage_fulfillment():
    """1 shift needs 2 people; 2 people available with correct skill → both
    assigned and coverage penalty is 0 (requirement fully met)."""
    solver = _make_solver()
    shift_id = "s_cov_full"

    context = SolverContext(
        people_ids=["p1", "p2"],
        tasks=[],
        coverage_requirements=[shift_id],
        shift_ids=[shift_id],
    )
    constraint_context = {
        "shift_metadata": _build_shift_meta(shift_id),
        "person_availability": {
            "p1": _full_availability(),
            "p2": _full_availability(),
        },
        "person_skills": {"p1": {"nurse"}, "p2": {"nurse"}},
        "skill_hierarchy": {},
        "required_skills": {shift_id: {"nurse"}},
    }
    scoring_context = {
        "coverage_requirements": [(shift_id, 2)],
        "offered_time_minutes": {},
    }

    assignments, result = solver.generate_initial(context, constraint_context, scoring_context)

    assert assignments is not None, f"Solver returned infeasible: {result}"
    assert len(assignments) == 2
    assert {a.person_id for a in assignments} == {"p1", "p2"}
    assert result["breakdown"]["coverage"] == 0.0  # fully fulfilled


# ---------------------------------------------------------------------------
# test_coverage_partial
# ---------------------------------------------------------------------------

def test_coverage_partial():
    """1 shift needs 2 people; only 1 person is available → 1 assigned,
    coverage penalty > 0 (requirement partially unmet)."""
    solver = _make_solver()
    shift_id = "s_cov_partial"

    context = SolverContext(
        people_ids=["p1", "p2"],
        tasks=[],
        coverage_requirements=[shift_id],
        shift_ids=[shift_id],
    )
    constraint_context = {
        "shift_metadata": _build_shift_meta(shift_id),
        "person_availability": {
            "p1": _full_availability(),
            "p2": [],  # p2 has no availability
        },
        "person_skills": {"p1": {"nurse"}, "p2": {"nurse"}},
        "skill_hierarchy": {},
        "required_skills": {shift_id: {"nurse"}},
    }
    scoring_context = {
        "coverage_requirements": [(shift_id, 2)],
        "offered_time_minutes": {},
    }

    assignments, result = solver.generate_initial(context, constraint_context, scoring_context)

    assert assignments is not None, f"Solver returned infeasible: {result}"
    assert len(assignments) == 1
    assert assignments[0].person_id == "p1"
    assert result["breakdown"]["coverage"] > 0.0  # partially fulfilled


# ---------------------------------------------------------------------------
# test_unavailable_not_assigned_even_with_skill
# ---------------------------------------------------------------------------

def test_unavailable_not_assigned_even_with_skill():
    """Person has correct skill but availability window does not cover the
    shift time → hard availability constraint forces 0 assignments."""
    solver = _make_solver()
    shift_id = "s_unavailable"

    context = SolverContext(
        people_ids=["alice"],
        tasks=[],
        coverage_requirements=[shift_id],
        shift_ids=[shift_id],
    )

    # Window ends two hours before the shift begins — does not cover [09:00, 17:00]
    non_covering = [(BASE.replace(hour=6), BASE.replace(hour=8))]

    constraint_context = {
        "shift_metadata": _build_shift_meta(shift_id),
        "person_availability": {"alice": non_covering},
        "person_skills": {"alice": {"nurse"}},
        "skill_hierarchy": {},
        "required_skills": {shift_id: {"nurse"}},
    }
    scoring_context = {
        "coverage_requirements": [(shift_id, 1)],
        "offered_time_minutes": {},
    }

    assignments, result = solver.generate_initial(context, constraint_context, scoring_context)

    assert assignments is not None, f"Solver returned infeasible: {result}"
    assert len(assignments) == 0
