import sys
import os
import json

import anthropic

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
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
    availableDays: list[str] = []          # ["mon", "tue", ...]
    availability: dict[str, str] = {}
    max_hours_per_day: float = 8.0
    min_rest_minutes: int = 30


class Role(BaseModel):
    id: str
    required_skill: str
    required_count: int = 1
    notes: str = ""


class ShiftDef(BaseModel):
    id: str
    name: str
    start: str
    end: str
    date: str = "2026-01-01"
    category: str = "Morning"
    shiftLeaderId: str = ""
    repeatDays: list[str] = []
    roles: list[Role] = []


class GenerateRequest(BaseModel):
    people: list[Person]
    shifts: list[ShiftDef]


class RoleAssignmentOut(BaseModel):
    role_id: str
    required_skill: str
    required_count: int
    notes: str
    assigned_person_ids: list[str]
    unfulfilled: int


class ScheduleEntryOut(BaseModel):
    shift_id: str
    date: str
    shift_leader_id: str = ""
    role_assignments: list[RoleAssignmentOut]
    total_unfulfilled: int


class GenerateResponse(BaseModel):
    schedule: list[ScheduleEntryOut]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    if not req.shifts:
        return GenerateResponse(schedule=[])

    DAY_MAP = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}

    from datetime import date as dt_date
    def get_day_key(date_str: str) -> str:
        d = dt_date.fromisoformat(date_str)
        return ["sun","mon","tue","wed","thu","fri","sat"][d.weekday() + 1 if d.weekday() < 6 else 0]

    # Expand shifts based on repeatDays
    from datetime import date as dt_date, timedelta
    today = dt_date.today()
    week_dates = [(today + timedelta(days=i)).isoformat() for i in range(7)]

    expanded = []  # (shift, date)
    for shift in req.shifts:
        expanded.append((shift, shift.date))
        for d in week_dates:
            if d != shift.date:
                day_key = get_day_key(d)
                if day_key in shift.repeatDays:
                    expanded.append((shift, d))

    schedule = []
    person_time_assignments: dict[str, set] = {}  # personId -> set of timekeys

    for shift, date in expanded:
        day_key = get_day_key(date)
        time_key = f"{date}-{shift.start}-{shift.end}"

        role_assignments = []
        total_unfulfilled = 0

        for role in shift.roles:
            assigned_ids = []
            eligible = [
                p for p in req.people
                if (not p.availableDays or day_key in p.availableDays)
                and (not role.required_skill or role.required_skill in p.skills)
            ]

            for person in eligible:
                if len(assigned_ids) >= role.required_count:
                    break
                assignments = person_time_assignments.get(person.id, set())
                if time_key not in assignments:
                    assigned_ids.append(person.id)
                    assignments.add(time_key)
                    person_time_assignments[person.id] = assignments

            unfulfilled = max(0, role.required_count - len(assigned_ids))
            total_unfulfilled += unfulfilled

            role_assignments.append(RoleAssignmentOut(
                role_id=role.id,
                required_skill=role.required_skill,
                required_count=role.required_count,
                notes=role.notes,
                assigned_person_ids=assigned_ids,
                unfulfilled=unfulfilled,
            ))

        schedule.append(ScheduleEntryOut(
            shift_id=shift.id,
            date=date,
            shift_leader_id=shift.shiftLeaderId or "",
            role_assignments=role_assignments,
            total_unfulfilled=total_unfulfilled,
        ))

    return GenerateResponse(schedule=schedule)


# ---------------------------------------------------------------------------
# Refine endpoint
# ---------------------------------------------------------------------------

class RefineRequest(BaseModel):
    instruction: str
    current_schedule: list
    people: list = []

class RefineResponse(BaseModel):
    updated_schedule: list
    explanation: str


@app.post("/api/refine", response_model=RefineResponse)
def refine(req: RefineRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    
    people_json = json.dumps(req.people, indent=2)
    schedule_json = json.dumps(req.current_schedule, indent=2)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=(
            "You are a shift scheduling assistant. "
            "The user will provide a current schedule (as JSON) and an instruction to modify it. "
            "Return a JSON object with exactly two keys: "
            '"updated_schedule" (the modified schedule as a list) and '
            '"explanation" (a brief plain-text explanation of the changes made). '
            "Respond with raw JSON only — no markdown, no code fences."
        ),
        messages=[
            {
                "role": "user",
                "content": (

                    f"People: {people_json}\n\n"
                    f"Current schedule:\n{schedule_json}\n\n"
                    f"Instruction: {req.instruction}"
                ),
            }
        ],
    )

    text = next(b.text for b in message.content if b.type == "text")
    data = json.loads(text)

    return RefineResponse(
        updated_schedule=data["updated_schedule"],
        explanation=data["explanation"],
    )


# ---------------------------------------------------------------------------
# New /api/solve endpoint — compatible with v0_project frontend
# ---------------------------------------------------------------------------
class SolvePerson(BaseModel):
    id: str
    name: str
    skills: list[str] = []
    maxShiftsPerDay: int = 1

class SolveTask(BaseModel):
    id: str
    name: str
    requiredSkill: str = ""
    category: str = "morning"

class SolveRequest(BaseModel):
    people: list[SolvePerson]
    tasks: list[SolveTask]
    date: str

class SolveEntry(BaseModel):
    id: str
    personId: str
    taskId: str
    date: str
    start: str
    end: str
    category: str
    isLeader: bool
    isOvernight: bool

class SolveResponse(BaseModel):
    entries: list[SolveEntry]

CATEGORY_TIMES = {
    "early_morning": ("06:00", "09:00"),
    "morning": ("09:00", "13:00"),
    "afternoon": ("13:00", "17:00"),
    "evening": ("17:00", "21:00"),
    "overnight": ("21:00", "04:00"),
}

import random, string

def new_id():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=7))

@app.post("/api/solve", response_model=SolveResponse)
def solve(req: SolveRequest):
    entries = []
    shifts_count = {p.id: 0 for p in req.people}
    leader_assigned = set()
    tasks_by_cat = {}
    for task in req.tasks:
        tasks_by_cat.setdefault(task.category, []).append(task)
    for category, cat_tasks in tasks_by_cat.items():
        start, end = CATEGORY_TIMES.get(category, ("09:00", "17:00"))
        for task in cat_tasks:
            eligible = [
                p for p in req.people
                if shifts_count[p.id] < p.maxShiftsPerDay
                and (not task.requiredSkill or task.requiredSkill in p.skills)
            ]
            if not eligible:
                eligible = [p for p in req.people if not task.requiredSkill or task.requiredSkill in p.skills]
            if not eligible:
                continue
            eligible.sort(key=lambda p: shifts_count[p.id])
            person = eligible[0]
            is_leader = category not in leader_assigned
            if is_leader:
                leader_assigned.add(category)
            entries.append(SolveEntry(
                id=new_id(),
                personId=person.id,
                taskId=task.id,
                date=req.date,
                start=start,
                end=end,
                category=category,
                isLeader=is_leader,
                isOvernight=(category == "overnight"),
            ))
            shifts_count[person.id] += 1
    return SolveResponse(entries=entries)


# ---------------------------------------------------------------------------
# Chat endpoint — proxies Anthropic API to avoid CORS
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    system: str = ""

class ChatResponse(BaseModel):
    reply: str

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=req.system,
        messages=[{"role": m.role, "content": m.content} for m in req.messages],
    )
    text = next(b.text for b in message.content if b.type == "text")
    return ChatResponse(reply=text)
