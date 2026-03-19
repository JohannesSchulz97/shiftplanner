from fastapi import APIRouter
from pydantic import BaseModel
import random, string

router = APIRouter()

def new_id():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=7))

CATEGORY_TIMES = {
    "early_morning": ("06:00", "09:00"),
    "morning": ("09:00", "13:00"),
    "afternoon": ("13:00", "17:00"),
    "evening": ("17:00", "21:00"),
    "overnight": ("21:00", "04:00"),
}

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

@router.post("/api/solve", response_model=SolveResponse)
def solve(req: SolveRequest):
    entries = []
    shifts_count: dict[str, int] = {p.id: 0 for p in req.people}
    leader_assigned: set[str] = set()

    tasks_by_cat: dict[str, list[SolveTask]] = {}
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
                eligible = [
                    p for p in req.people
                    if not task.requiredSkill or task.requiredSkill in p.skills
                ]
            if not eligible:
                continue
            eligible.sort(key=lambda p: shifts_count[p.id])
            person = eligible[0]
            is_leader = category not in leader_assigned
            if is_leader:
                leader_assigned.add(category)
            is_overnight = category == "overnight"
            entries.append(SolveEntry(
                id=new_id(),
                personId=person.id,
                taskId=task.id,
                date=req.date,
                start=start,
                end=end,
                category=category,
                isLeader=is_leader,
                isOvernight=is_overnight,
            ))
            shifts_count[person.id] += 1

    return SolveResponse(entries=entries)
