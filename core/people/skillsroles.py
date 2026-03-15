 class Person:
       2     def __init__(self, name: str, skills: set[str] | None = None, roles: set[str] | None = None) -> None:
       3         self.name = name
       4         self.skills: set[str] = set(skills) if skills else set()
       5         self.roles: set[str] = set(roles) if roles else set()
       6
       7     @staticmethod
       8     def _validate(value: str, label: str) -> str:
       9         stripped = value.strip()
      10         if not stripped:
      11             raise ValueError(f"{label} must not be empty or whitespace")
      12         return stripped
      13
      14     def add_skill(self, skill: str) -> None:
      15         self.skills.add(self._validate(skill, "skill"))
      16
      17     def remove_skill(self, skill: str) -> None:
      18         self.skills.discard(self._validate(skill, "skill"))
      19
      20     def has_skill(self, skill: str) -> bool:
      21         return self._validate(skill, "skill") in self.skills
      22
      23     def add_role(self, role: str) -> None:
      24         self.roles.add(self._validate(role, "role"))
      25
      26     def remove_role(self, role: str) -> None:
      27         self.roles.discard(self._validate(role, "role"))
      28
      29     def has_role(self, role: str) -> bool:
      30         return self._validate(role, "role") in self.roles
      31
      32     def __repr__(self) -> str:
      33         return f"Person(name={self.name!r}, skills={self.skills!r}, roles={self.roles!r})"
