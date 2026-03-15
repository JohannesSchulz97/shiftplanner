"""Tests for the CP-SAT solver (solver/solver.py).

Each test is self-contained and builds its own SolverContext,
constraint_context, and scoring_context from scratch.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta

import pytest

# Make sure the project root is on sys.path regardless of how pytest is invoked.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from solver.solver import Solver
from solver.solver_context import SolverContext
from solver.constraint_engine import ConstraintEngine
from solver.scoring_engine import ScoringEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATE = datetime(2026, 3, 14)


def _dt(hour: int, minute: int = 0) -> datetime:
    """Return a datetime on the test date at the given hour:minute."""
    return DATE.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _make_solver() -> Solver:
    return Solver(ConstraintEngine(), ScoringEngine())


def _shift_meta(
    assignment_id: str,
    start: datetime,
    end: datetime,
    assignment_type: str = "coverage",
    location_id: str = "loc1",
) -> dict:
    return {
        "assignment_type": assignment_type,
        "assignment_id": assignment_id,
        "location_id": location_id,
        "start_datetime": start,
        "end_datetime": end,
    }


def _full_day_window() -> list[tuple[datetime, datetime]]:
    """Availability window spanning the entire test date."""
    return [(_dt(0), _dt(23, 59))]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_basic_assignment():
    """1 person with the correct skill, 1 shift → person is assigned."""
    solver = _make_solver()

    context = SolverContext(
        people_ids=["p1"],
        tasks=[],
        coverage_requirements=["s1"],
        shift_ids=["s1"],
    )

    constraint_context = {
        "shift_metadata": {
            "s1": _shift_meta("cov1", _dt(9), _dt(12)),
        },
        "person_skills": {"p1": {"nurse"}},
        "skill_hierarchy": {},
        "required_skills": {"cov1": {"nurse"}},
        "person_availability": {"p1": _full_day_window()},
        "max_hours_per_day": {},
        "minimum_rest_minutes": {},
    }

    scoring_context = {
        "coverage_requirements": [("s1", 1)],
        "offered_time_minutes": {"p1": 180},
    }

    assignments, result = solver.generate_initial(context, constraint_context, scoring_context)

    assert assignments is not None, "Expected a feasible solution"
    assert len(assignments) == 1
    assert assignments[0].person_id == "p1"
    assert assignments[0].shift_id == "s1"


def test_skill_mismatch():
    """1 person with the wrong skill, 1 shift → no assignment (unfulfilled)."""
    solver = _make_solver()

    context = SolverContext(
        people_ids=["p1"],
        tasks=[],
        coverage_requirements=["s1"],
        shift_ids=["s1"],
    )

    constraint_context = {
        "shift_metadata": {
            "s1": _shift_meta("cov1", _dt(9), _dt(12)),
        },
        "person_skills": {"p1": {"cook"}},       # wrong skill
        "skill_hierarchy": {},
        "required_skills": {"cov1": {"nurse"}},  # needs nurse
        "person_availability": {"p1": _full_day_window()},
        "max_hours_per_day": {},
        "minimum_rest_minutes": {},
    }

    scoring_context = {
        "coverage_requirements": [("s1", 1)],
        "offered_time_minutes": {},
    }

    assignments, result = solver.generate_initial(context, constraint_context, scoring_context)

    # Solver is still feasible (empty assignment satisfies all hard constraints),
    # but no one can be assigned to the shift.
    assert assignments is not None
    assert len(assignments) == 0, "No assignment expected due to skill mismatch"


def test_unavailable_person():
    """Person's availability window does not cover the shift → not assigned."""
    solver = _make_solver()

    context = SolverContext(
        people_ids=["p1"],
        tasks=[],
        coverage_requirements=["s1"],
        shift_ids=["s1"],
    )

    # Shift is 14:00–17:00; person is only available 08:00–12:00.
    constraint_context = {
        "shift_metadata": {
            "s1": _shift_meta("cov1", _dt(14), _dt(17)),
        },
        "person_skills": {"p1": {"nurse"}},
        "skill_hierarchy": {},
        "required_skills": {"cov1": {"nurse"}},
        "person_availability": {"p1": [(_dt(8), _dt(12))]},  # doesn't cover shift
        "max_hours_per_day": {},
        "minimum_rest_minutes": {},
    }

    scoring_context = {
        "coverage_requirements": [("s1", 1)],
        "offered_time_minutes": {},
    }

    assignments, result = solver.generate_initial(context, constraint_context, scoring_context)

    assert assignments is not None
    assert len(assignments) == 0, "Person is unavailable during the shift"


def test_offered_person_gets_assigned():
    """Person with 'offered' availability (window covering shift) → gets assigned."""
    solver = _make_solver()

    context = SolverContext(
        people_ids=["p1"],
        tasks=[],
        coverage_requirements=["s1"],
        shift_ids=["s1"],
    )

    # 'Offered' availability is modelled the same as 'available' in the solver:
    # a time window that fully contains the shift is sufficient for assignment.
    constraint_context = {
        "shift_metadata": {
            "s1": _shift_meta("cov1", _dt(9), _dt(12)),
        },
        "person_skills": {"p1": {"nurse"}},
        "skill_hierarchy": {},
        "required_skills": {"cov1": {"nurse"}},
        "person_availability": {"p1": [(_dt(8), _dt(13))]},  # offered window
        "max_hours_per_day": {},
        "minimum_rest_minutes": {},
    }

    scoring_context = {
        "coverage_requirements": [("s1", 1)],
        "offered_time_minutes": {"p1": 180},
    }

    assignments, result = solver.generate_initial(context, constraint_context, scoring_context)

    assert assignments is not None
    assert len(assignments) == 1
    assert assignments[0].person_id == "p1"


def test_no_overlap():
    """1 person, 2 overlapping shifts → person assigned to exactly one."""
    solver = _make_solver()

    # s1: 09:00–13:00, s2: 11:00–15:00 — they overlap.
    context = SolverContext(
        people_ids=["p1"],
        tasks=[],
        coverage_requirements=["s1", "s2"],
        shift_ids=["s1", "s2"],
    )

    constraint_context = {
        "shift_metadata": {
            "s1": _shift_meta("cov1", _dt(9), _dt(13)),
            "s2": _shift_meta("cov2", _dt(11), _dt(15)),
        },
        "person_skills": {"p1": {"nurse"}},
        "skill_hierarchy": {},
        "required_skills": {"cov1": {"nurse"}, "cov2": {"nurse"}},
        "person_availability": {"p1": _full_day_window()},
        "max_hours_per_day": {},
        "minimum_rest_minutes": {},
    }

    scoring_context = {
        "coverage_requirements": [("s1", 1), ("s2", 1)],
        "offered_time_minutes": {"p1": 480},
    }

    assignments, result = solver.generate_initial(context, constraint_context, scoring_context)

    assert assignments is not None
    assigned_to_p1 = [a for a in assignments if a.person_id == "p1"]
    assert len(assigned_to_p1) == 1, "Person can only be assigned to one of two overlapping shifts"


def test_two_people_two_shifts():
    """2 people, 2 non-overlapping shifts with different required skills → both fulfilled."""
    solver = _make_solver()

    # p1 is a nurse → assigned to s1 (needs nurse, 09:00–12:00)
    # p2 is a doctor → assigned to s2 (needs doctor, 13:00–16:00)
    context = SolverContext(
        people_ids=["p1", "p2"],
        tasks=[],
        coverage_requirements=["s1", "s2"],
        shift_ids=["s1", "s2"],
    )

    constraint_context = {
        "shift_metadata": {
            "s1": _shift_meta("cov1", _dt(9), _dt(12)),
            "s2": _shift_meta("cov2", _dt(13), _dt(16)),
        },
        "person_skills": {
            "p1": {"nurse"},
            "p2": {"doctor"},
        },
        "skill_hierarchy": {},
        "required_skills": {
            "cov1": {"nurse"},
            "cov2": {"doctor"},
        },
        "person_availability": {
            "p1": _full_day_window(),
            "p2": _full_day_window(),
        },
        "max_hours_per_day": {},
        "minimum_rest_minutes": {},
    }

    scoring_context = {
        "coverage_requirements": [("s1", 1), ("s2", 1)],
        "offered_time_minutes": {"p1": 180, "p2": 180},
    }

    assignments, result = solver.generate_initial(context, constraint_context, scoring_context)

    assert assignments is not None
    assert len(assignments) == 2

    shift_ids_assigned = {a.shift_id for a in assignments}
    assert "s1" in shift_ids_assigned
    assert "s2" in shift_ids_assigned

    p1_assignments = [a for a in assignments if a.person_id == "p1"]
    p2_assignments = [a for a in assignments if a.person_id == "p2"]
    assert len(p1_assignments) == 1 and p1_assignments[0].shift_id == "s1"
    assert len(p2_assignments) == 1 and p2_assignments[0].shift_id == "s2"


def test_max_hours_respected():
    """Person with max_hours_per_day=3, two 3-hour shifts → only one shift assigned."""
    solver = _make_solver()

    # s1: 09:00–12:00 (3 h), s2: 13:00–16:00 (3 h) — total would be 6 h > limit.
    context = SolverContext(
        people_ids=["p1"],
        tasks=[],
        coverage_requirements=["s1", "s2"],
        shift_ids=["s1", "s2"],
    )

    constraint_context = {
        "shift_metadata": {
            "s1": _shift_meta("cov1", _dt(9), _dt(12)),
            "s2": _shift_meta("cov2", _dt(13), _dt(16)),
        },
        "person_skills": {"p1": {"nurse"}},
        "skill_hierarchy": {},
        "required_skills": {"cov1": {"nurse"}, "cov2": {"nurse"}},
        "person_availability": {"p1": _full_day_window()},
        "max_hours_per_day": {"p1": 3.0},  # 3-hour cap
        "minimum_rest_minutes": {},
    }

    scoring_context = {
        "coverage_requirements": [("s1", 1), ("s2", 1)],
        "offered_time_minutes": {"p1": 360},
    }

    assignments, result = solver.generate_initial(context, constraint_context, scoring_context)

    assert assignments is not None
    assert len(assignments) == 1, "Max-hours cap should prevent assignment to both shifts"
    assert assignments[0].person_id == "p1"


def test_infeasible_returns_none():
    """No people in context → solver returns (None, report) immediately."""
    solver = _make_solver()

    context = SolverContext(
        people_ids=[],       # no people
        tasks=[],
        coverage_requirements=["s1"],
        shift_ids=["s1"],
    )

    constraint_context = {
        "shift_metadata": {
            "s1": _shift_meta("cov1", _dt(9), _dt(12)),
        },
        "person_skills": {},
        "skill_hierarchy": {},
        "required_skills": {"cov1": {"nurse"}},
        "person_availability": {},
        "max_hours_per_day": {},
        "minimum_rest_minutes": {},
    }

    scoring_context = {
        "coverage_requirements": [("s1", 1)],
        "offered_time_minutes": {},
    }

    assignments, report = solver.generate_initial(context, constraint_context, scoring_context)

    assert assignments is None, "Expected None when no people are available"
    assert report is not None
    assert "failed_constraints" in report
