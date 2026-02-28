from enum import Enum


class TaskPriority(Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"


class Task:
    """A specific named deliverable to be completed during a planning period.

    Defines what needs to be done, who can do it (via required skills),
    how long it takes, and any constraints on assignment.
    """

    def __init__(
        self,
        name: str,
        required_skills: set[str],
        duration: float,
        splittable: bool = False,
        location: str | None = None,
        resources: set[str] | None = None,
        priority: TaskPriority = TaskPriority.OPTIONAL,
        min_team_size: int = 1,
        max_team_size: int = 1,
        dependencies: list[str] | None = None,
    ) -> None:
        self.name = self._validate_str(name, "name")
        self.required_skills = self._validate_skills(required_skills)
        self.duration = self._validate_duration(duration)
        self.splittable = splittable
        self.location = location
        self.resources: set[str] = set(resources) if resources else set()
        self.priority = priority
        self.min_team_size, self.max_team_size = self._validate_team_size(min_team_size, max_team_size)
        self.dependencies: list[str] = list(dependencies) if dependencies else []

    @staticmethod
    def _validate_str(value: str, label: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{label} must not be empty or whitespace")
        return stripped

    @staticmethod
    def _validate_skills(skills: set[str]) -> set[str]:
        if not skills:
            raise ValueError("required_skills must not be empty")
        return set(skills)

    @staticmethod
    def _validate_duration(duration: float) -> float:
        if duration <= 0:
            raise ValueError(f"duration must be a positive number, got {duration}")
        return float(duration)

    @staticmethod
    def _validate_team_size(min_size: int, max_size: int) -> tuple[int, int]:
        if min_size < 1:
            raise ValueError(f"min_team_size must be at least 1, got {min_size}")
        if max_size < min_size:
            raise ValueError(f"max_team_size ({max_size}) must be >= min_team_size ({min_size})")
        return min_size, max_size

    def __repr__(self) -> str:
        return (
            f"Task(name={self.name!r}, required_skills={self.required_skills!r}, "
            f"duration={self.duration}, priority={self.priority!r})"
        )
