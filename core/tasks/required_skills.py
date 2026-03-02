from __future__ import annotations


class RequiredSkills:
    """The set of skills that must be held by a person assigned to a task.

    A task requires at least one skill. Skills are referenced by identifier
    (str), consistent with the People domain. This class is immutable after
    construction — the required skill set cannot be changed once defined.
    """

    __slots__ = ("_skills",)

    def __init__(self, skills: set[str] | frozenset[str]) -> None:
        normalized = frozenset(s.strip().lower() for s in skills)
        empty = {s for s in normalized if not s}
        if empty or not normalized:
            raise ValueError("RequiredSkills must contain at least one non-empty skill identifier.")
        self._skills: frozenset[str] = normalized

    @property
    def skills(self) -> frozenset[str]:
        """The immutable set of required skill identifiers."""
        return self._skills

    def includes(self, skill: str) -> bool:
        """Return True if the given skill is among the required skills."""
        return skill.strip() in self._skills

    def is_satisfied_by(self, available: set[str]) -> bool:
        """Return True if all required skills are present in the given skill set."""
        return self._skills.issubset({s.strip() for s in available})
    def __repr__(self) -> str:
        return f"RequiredSkills(skills={set(self._skills)!r})"


