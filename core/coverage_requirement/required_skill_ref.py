from __future__ import annotations


class RequiredSkillRef:
    """Reference to the skill that assigned people must possess for a coverage requirement.

    Holds a normalized skill identifier (stripped, lowercase).
    Does not reference People domain classes — only stores the identifier.
    Immutable after construction.
    """

    __slots__ = ("_value",)

    def __init__(self, skill_id: str) -> None:
        if not isinstance(skill_id, str):
            raise ValueError(f"skill_id must be a str, got {type(skill_id).__name__!r}.")
        normalized = skill_id.strip().lower()
        if not normalized:
            raise ValueError("skill_id must not be empty or whitespace.")
        self._value: str = normalized

    @property
    def value(self) -> str:
        """The normalized skill identifier."""
        return self._value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, RequiredSkillRef):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"RequiredSkillRef({self._value!r})"
