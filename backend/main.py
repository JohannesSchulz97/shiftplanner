import sys
import os

# Ensure project root is on sys.path so solver/core/constraints_model imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from solver.constraint_engine import ConstraintEngine
from solver.scoring_engine import ScoringEngine
from solver.solver import Solver
from request_adapter import build_solver_inputs

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
# Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    if not req.shifts:
        return GenerateResponse(assignments=[])

    shifts = req.shifts
    context, constraint_context, scoring_context = build_solver_inputs(
        req.people, shifts
    )

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
