from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ShiftPlanner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request / response models ---

class Person(BaseModel):
    id: str
    name: str
    skills: list[str]
    available: bool = True


class ShiftDef(BaseModel):
    id: str
    name: str
    start: str          # "HH:MM"
    end: str            # "HH:MM"
    required_skill: str
    required_count: int = 1


class GenerateRequest(BaseModel):
    people: list[Person]
    shifts: list[ShiftDef]


class Assignment(BaseModel):
    shift_id: str
    person_ids: list[str]
    fulfilled: bool


class GenerateResponse(BaseModel):
    assignments: list[Assignment]


# --- Scheduling logic ---

def time_to_min(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def overlaps(s1: int, e1: int, s2: int, e2: int) -> bool:
    return not (e1 <= s2 or s1 >= e2)


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    # Work through shifts in chronological order
    shifts = sorted(req.shifts, key=lambda s: time_to_min(s.start))

    # Track which time windows each person is already committed to
    busy: dict[str, list[tuple[int, int]]] = {p.id: [] for p in req.people}

    assignments: list[Assignment] = []

    for shift in shifts:
        s_start = time_to_min(shift.start)
        s_end = time_to_min(shift.end)
        assigned: list[str] = []

        for person in req.people:
            if len(assigned) >= shift.required_count:
                break
            if not person.available:
                continue
            if shift.required_skill not in person.skills:
                continue
            # No overlap with an existing commitment
            if not any(overlaps(s_start, s_end, b, e) for b, e in busy[person.id]):
                assigned.append(person.id)
                busy[person.id].append((s_start, s_end))

        assignments.append(Assignment(
            shift_id=shift.id,
            person_ids=assigned,
            fulfilled=len(assigned) >= shift.required_count,
        ))

    return GenerateResponse(assignments=assignments)
