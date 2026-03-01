     1 from __future__ import annotations
       2
       3
       4 class RequiredSkillRef:
       5     """Reference to the skill that assigned people must possess for a coverage requirement.
       6
       7     Holds a normalized skill identifier (stripped, lowercase).
       8     Does not reference People domain classes — only stores the identifier.
       9     Immutable after construction.
      10     """
      11
      12     __slots__ = ("_value",)
      13
      14     def __init__(self, skill_id: str) -> None:
      15         if not isinstance(skill_id, str):
      16             raise ValueError(f"skill_id must be a str, got {type(skill_id).__name__!r}.")
      17         normalized = skill_id.strip().lower()
      18         if not normalized:
      19             raise ValueError("skill_id must not be empty or whitespace.")
      20         self._value: str = normalized
      21
      22     @property
      23     def value(self) -> str:
      24         """The normalized skill identifier."""
      25         return self._value
      26
      27     def __eq__(self, other: object) -> bool:
      28         if isinstance(other, RequiredSkillRef):
      29             return self._value == other._value
      30         return NotImplemented
      31
      32     def __hash__(self) -> int:
      33         return hash(self._value)
      34
      35     def __repr__(self) -> str:
      36         return f"RequiredSkillRef({self._value!r})"
