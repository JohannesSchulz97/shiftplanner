import sys
import os

# Ensure project root on sys.path when adapter is imported standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from solver.solver_context import SolverContext


def _parse_hhmm(hhmm: str) -> tuple[int, int]:
    h, m = hhmm.strip().split(":")
    return int(h), int(m)


def _to_datetime(date_str: str, hhmm: str) -> datetime:
    h, m = _parse_hhmm(hhmm)
    y, mo, d = (int(x) for x in date_str.split("-"))
    return datetime(y, mo, d, h, m)


def _available_windows(person, shift_date: str) -> list[tuple[datetime, datetime]]:
    """Return datetime windows where person is expected or offered (not unavailable)."""
    windows = []
    for time_range, state in person.availability.items():
        if state.lower() not in ("expected", "offered"):
            continue
        try:
            start_str, end_str = time_range.split("-")
            w_start = _to_datetime(shift_date, start_str.strip())
            w_end = _to_datetime(shift_date, end_str.strip())
            if w_start < w_end:
                windows.append((w_start, w_end))
        except (ValueError, AttributeError):
            continue
    if not windows:
        y, mo, d = (int(x) for x in shift_date.split("-"))
        windows.append((datetime(y, mo, d, 0, 0), datetime(y, mo, d, 23, 59)))
    return windows


def _offered_minutes(person, shift_date: str) -> int:
    """Sum minutes where state is OFFERED for the given date."""
    total = 0
    for time_range, state in person.availability.items():
        if state.lower() != "offered":
            continue
        try:
            start_str, end_str = time_range.split("-")
            w_start = _to_datetime(shift_date, start_str.strip())
            w_end = _to_datetime(shift_date, end_str.strip())
            total += int((w_end - w_start).total_seconds() / 60)
        except (ValueError, AttributeError):
            continue
    return total


def build_solver_inputs(people, shifts) -> tuple[SolverContext, dict, dict]:
    """Convert Pydantic request models into solver-ready context objects.

    Args:
        people: list of Person Pydantic models
        shifts: list of ShiftDef Pydantic models

    Returns:
        (context, constraint_context, scoring_context) ready for Solver.generate_initial()
    """
    all_dates = list({s.date for s in shifts})

    # shift_metadata: shift_id → {start_datetime, end_datetime, location_id, ...}
    shift_metadata: dict[str, dict] = {}
    for s in shifts:
        shift_metadata[s.id] = {
            "start_datetime":  _to_datetime(s.date, s.start),
            "end_datetime":    _to_datetime(s.date, s.end),
            "location_id":     "default",
            "assignment_type": "coverage",
            "assignment_id":   s.id,
        }

    # person_skills: person_id → set of skill strings
    person_skills: dict[str, set[str]] = {p.id: set(p.skills) for p in people}

    # skill_hierarchy: flat skills, no hierarchy
    skill_hierarchy: dict[str, set[str]] = {}

    # required_skills: shift_id → set of required skill strings
    required_skills: dict[str, set[str]] = {s.id: {s.required_skill} for s in shifts}

    # person_availability: person_id → list of (start, end) datetime windows
    person_availability: dict[str, list[tuple[datetime, datetime]]] = {}
    for p in people:
        windows: list[tuple[datetime, datetime]] = []
        for d in all_dates:
            windows.extend(_available_windows(p, d))
        person_availability[p.id] = windows

    # max_hours_per_day: person_id → float
    max_hours_per_day: dict[str, float] = {p.id: p.max_hours_per_day for p in people}

    # minimum_rest_minutes: person_id → int
    minimum_rest_minutes: dict[str, int] = {p.id: p.min_rest_minutes for p in people}

    # coverage_requirements: list of (shift_id, required_count)
    coverage_requirements: list[tuple[str, int]] = [
        (s.id, s.required_count) for s in shifts
    ]

    # offered_time_minutes: person_id → total offered minutes across all dates
    offered_time_minutes: dict[str, int] = {}
    for p in people:
        total = sum(_offered_minutes(p, d) for d in all_dates)
        if total > 0:
            offered_time_minutes[p.id] = total

    context = SolverContext(
        people_ids=[p.id for p in people],
        tasks=[],
        coverage_requirements=[s.id for s in shifts],
        shift_ids=[s.id for s in shifts],
    )

    constraint_context = {
        "shift_metadata":       shift_metadata,
        "person_skills":        person_skills,
        "skill_hierarchy":      skill_hierarchy,
        "required_skills":      required_skills,
        "person_availability":  person_availability,
        "max_hours_per_day":    max_hours_per_day,
        "minimum_rest_minutes": minimum_rest_minutes,
        "resource_assignments": [],
    }

    scoring_context = {
        "coverage_requirements": coverage_requirements,
        "offered_time_minutes":  offered_time_minutes,
        "required_tasks":        set(),
        "optional_tasks":        set(),
        "preferred_windows":     {},
        "previous_assignments":  [],
    }

    return context, constraint_context, scoring_context
