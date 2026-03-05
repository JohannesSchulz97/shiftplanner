import sys
import os

# Ensure project root is on sys.path so solver/core/constraints_model imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date as date_type
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from solver.solver_context import SolverContext
from solver.constraint_engine import ConstraintEngine
from solver.scoring_engine import ScoringEngine
from solver.solver import Solver

app = FastAPI(title="ShiftPlanner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class Person(BaseModel):
    id: str
    name: str
    skills: list[str]
    availability: dict[str, str] = {}       # {"08:00-11:00": "expected"}
    max_hours_per_day: float = 8.0
    min_rest_minutes: int = 30


class ShiftDef(BaseModel):
    id: str
    name: str
    start: str                              # "HH:MM"
    end: str                                # "HH:MM"
    required_skill: str
    required_count: int = 1
    date: str = "2026-01-01"               # "YYYY-MM-DD"


class GenerateRequest(BaseModel):
    people: list[Person]
    shifts: list[ShiftDef]


class AssignmentOut(BaseModel):
    shift_id: str
    person_ids: list[str]
    fulfilled: bool


class GenerateResponse(BaseModel):
    assignments: list[AssignmentOut]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_hhmm(hhmm: str) -> tuple[int, int]:
    h, m = hhmm.strip().split(":")
    return int(h), int(m)


def _to_datetime(date_str: str, hhmm: str) -> datetime:
    h, m = _parse_hhmm(hhmm)
    y, mo, d = (int(x) for x in date_str.split("-"))
    return datetime(y, mo, d, h, m)


def _available_windows(
    person: Person, shift_date: str
) -> list[tuple[datetime, datetime]]:
    """Parse person availability into datetime windows for the given date.

    Only EXPECTED and OFFERED states produce windows (UNAVAILABLE is excluded).
    """
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
    # If no availability declared, treat entire day as available
    if not windows:
        y, mo, d = (int(x) for x in shift_date.split("-"))
        windows.append((datetime(y, mo, d, 0, 0), datetime(y, mo, d, 23, 59)))
    return windows


def _offered_minutes(person: Person, shift_date: str) -> int:
    """Sum minutes where state is OFFERED."""
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


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    if not req.shifts:
        return GenerateResponse(assignments=[])

    people = req.people
    shifts = req.shifts

    # --- shift_metadata ---------------------------------------------------
    # shift_id → {start_datetime, end_datetime, location_id,
    #              assignment_type, assignment_id}
    shift_metadata: dict[str, dict] = {}
    for s in shifts:
        shift_metadata[s.id] = {
            "start_datetime": _to_datetime(s.date, s.start),
            "end_datetime":   _to_datetime(s.date, s.end),
            "location_id":    "default",
            "assignment_type": "coverage",
            "assignment_id":   s.id,
        }

    # --- person_skills ----------------------------------------------------
    person_skills: dict[str, set[str]] = {p.id: set(p.skills) for p in people}

    # --- skill_hierarchy --------------------------------------------------
    skill_hierarchy: dict[str, set[str]] = {}  # flat skills — no hierarchy

    # --- required_skills per shift ----------------------------------------
    required_skills: dict[str, set[str]] = {s.id: {s.required_skill} for s in shifts}

    # --- person_availability (per-date windows) ---------------------------
    # Use the date of the first shift for each person's window parsing.
    # If shifts span multiple dates, each shift uses its own date.
    # We build a unified window list covering all shift dates.
    all_dates = list({s.date for s in shifts})
    person_availability: dict[str, list[tuple[datetime, datetime]]] = {}
    for p in people:
        windows: list[tuple[datetime, datetime]] = []
        for d in all_dates:
            windows.extend(_available_windows(p, d))
        person_availability[p.id] = windows

    # --- max_hours_per_day ------------------------------------------------
    max_hours_per_day: dict[str, float] = {p.id: p.max_hours_per_day for p in people}

    # --- minimum_rest_minutes ---------------------------------------------
    minimum_rest_minutes: dict[str, int] = {p.id: p.min_rest_minutes for p in people}

    # --- coverage_requirements --------------------------------------------
    coverage_requirements: list[tuple[str, int]] = [
        (s.id, s.required_count) for s in shifts
    ]

    # --- offered_time_minutes ---------------------------------------------
    # Sum offered minutes across all shift dates per person
    offered_time_minutes: dict[str, int] = {}
    for p in people:
        total = sum(_offered_minutes(p, d) for d in all_dates)
        if total > 0:
            offered_time_minutes[p.id] = total

    # --- assemble contexts ------------------------------------------------
    context = SolverContext(
        people_ids=[p.id for p in people],
        tasks=[],
        coverage_requirements=[s.id for s in shifts],
        shift_ids=[s.id for s in shifts],
    )

    constraint_context = {
        "shift_metadata":      shift_metadata,
        "person_skills":       person_skills,
        "skill_hierarchy":     skill_hierarchy,
        "required_skills":     required_skills,
        "person_availability": person_availability,
        "max_hours_per_day":   max_hours_per_day,
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

    # --- solve ------------------------------------------------------------
    solver = Solver(ConstraintEngine(), ScoringEngine())
    assignments_result, result_meta = solver.generate_initial(
        context, constraint_context, scoring_context
    )

    if assignments_result is None:
        # Return unfulfilled slots rather than 500
        return GenerateResponse(assignments=[
            AssignmentOut(shift_id=s.id, person_ids=[], fulfilled=False)
            for s in shifts
        ])

    # --- group results by shift_id ----------------------------------------
    shift_persons: dict[str, list[str]] = defaultdict(list)
    for a in assignments_result:
        shift_persons[a.shift_id].append(a.person_id)

    shift_required = {s.id: s.required_count for s in shifts}
    out = [
        AssignmentOut(
            shift_id=s.id,
            person_ids=shift_persons.get(s.id, []),
            fulfilled=len(shift_persons.get(s.id, [])) >= shift_required[s.id],
        )
        for s in shifts
    ]

    return GenerateResponse(assignments=out)
