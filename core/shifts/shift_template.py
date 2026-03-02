from datetime import time
from enum import Enum

from core.shifts.shift import Shift


class PlanningHorizon(Enum):
    """The temporal scope of a shift template's planning cycle.

    DAILY:   Template covers a single day.
    WEEKLY:  Template covers a full week.
    MONTHLY: Template covers a calendar month.
    AD_HOC:  Template has no fixed recurring horizon; used for one-off periods.
    """

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    AD_HOC = "ad_hoc"


class ShiftTemplate:
    """A reusable collection of shifts defining the structure of a planning cycle.

    A ShiftTemplate describes WHEN work may exist across a planning period.
    It holds a set of Shift objects and serves as the structural blueprint
    used when generating concrete schedules. It contains no assignments or people.

    Templates can be serialized and reapplied across planning cycles via
    to_dict() and from_dict().
    """

    def __init__(self, name: str, horizon: PlanningHorizon) -> None:
        stripped = name.strip()
        if not stripped:
            raise ValueError("name must not be empty or whitespace")
        self.name = stripped
        self.horizon = horizon
        self._shifts: list[Shift] = []

    def _is_duplicate(self, shift: Shift) -> bool:
        return any(
            s.name == shift.name
            and s.day == shift.day
            and s.start_time == shift.start_time
            and s.end_time == shift.end_time
            for s in self._shifts
        )

    def add_shift(self, shift: Shift) -> None:
        """Add a shift to the template. Raises ValueError if an identical shift already exists."""
        if self._is_duplicate(shift):
            raise ValueError(f"Duplicate shift: {shift!r}")
        self._shifts.append(shift)

    def remove_shift(self, shift: Shift) -> None:
        """Remove a shift from the template. Silent no-op if not present."""
        self._shifts = [
            s for s in self._shifts
            if not (
                s.name == shift.name
                and s.day == shift.day
                and s.start_time == shift.start_time
                and s.end_time == shift.end_time
            )
        ]

    def shifts_for_day(self, day: str) -> list[Shift]:
        """Return all shifts scheduled on the given day."""
        return [s for s in self._shifts if s.day == day.strip()]

    def all_shifts(self) -> list[Shift]:
        """Return a copy of all shifts in the template."""
        return list(self._shifts)

    def to_dict(self) -> dict:
        """Serialize the template to a plain dictionary for storage or transfer."""
        return {
            "name": self.name,
            "horizon": self.horizon.value,
            "shifts": [
                {
                    "name": s.name,
                    "day": s.day,
                    "start_time": s.start_time.strftime("%H:%M"),
                    "end_time": s.end_time.strftime("%H:%M"),
                }
                for s in self._shifts
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShiftTemplate":
        """Reconstruct a ShiftTemplate from a serialized dictionary."""
        template = cls(
            name=data["name"],
            horizon=PlanningHorizon(data["horizon"]),
        )
        for s in data["shifts"]:
            start_h, start_m = map(int, s["start_time"].split(":"))
            end_h, end_m = map(int, s["end_time"].split(":"))
            template.add_shift(Shift(
                name=s["name"],
                day=s["day"],
                start_time=time(start_h, start_m),
                end_time=time(end_h, end_m),
            ))
        return template

    def __repr__(self) -> str:
        return (
            f"ShiftTemplate(name={self.name!r}, horizon={self.horizon.name}, "
            f"shifts={len(self._shifts)})"
        )
