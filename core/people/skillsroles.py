from .availability import Availability
from .limitations import Limitations
from .working_hours import WorkingHours
from .rest_period import RestPeriod


class Person:
    def __init__(
        self,
        name: str,
        skills: set[str] | None = None,
        roles: set[str] | None = None,
        working_hours: WorkingHours | None = None,
        rest_period: RestPeriod | None = None,
    ) -> None:
        self.name = name
        self.skills: set[str] = set(skills) if skills else set()
        self.roles: set[str] = set(roles) if roles else set()
        self.availability: Availability = Availability()
        self.limitations: Limitations = Limitations()
        self.working_hours: WorkingHours | None = working_hours
        self.rest_period: RestPeriod | None = rest_period

    @staticmethod
    def _validate(value: str, label: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{label} must not be empty or whitespace")
        return stripped

    def add_skill(self, skill: str) -> None:
        self.skills.add(self._validate(skill, "skill"))

    def remove_skill(self, skill: str) -> None:
        self.skills.discard(self._validate(skill, "skill"))

    def has_skill(self, skill: str) -> bool:
        return self._validate(skill, "skill") in self.skills

    def add_role(self, role: str) -> None:
        self.roles.add(self._validate(role, "role"))

    def remove_role(self, role: str) -> None:
        self.roles.discard(self._validate(role, "role"))

    def has_role(self, role: str) -> bool:
        return self._validate(role, "role") in self.roles

    def __repr__(self) -> str:
        return f"Person(name={self.name!r}, skills={self.skills!r}, roles={self.roles!r})"
