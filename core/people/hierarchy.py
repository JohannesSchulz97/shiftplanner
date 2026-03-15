    1 class SkillHierarchy:
       2     def __init__(self) -> None:
       3         self._rules: dict[str, set[str]] = {}
       4
       5     @staticmethod
       6     def _validate(value: str, label: str) -> str:
       7         stripped = value.strip()
       8         if not stripped:
       9             raise ValueError(f"{label} must not be empty or whitespace")
      10         return stripped
      11
      12     def add_rule(self, higher: str, lower: str) -> None:
      13         higher = self._validate(higher, "higher")
      14         lower = self._validate(lower, "lower")
      15         self._rules.setdefault(higher, set()).add(lower)
      16
      17     def remove_rule(self, higher: str, lower: str) -> None:
      18         higher = self._validate(higher, "higher")
      19         lower = self._validate(lower, "lower")
      20         if higher in self._rules:
      21             self._rules[higher].discard(lower)
      22
      23     def can_cover(self, higher: str, required: str) -> bool:
      24         higher = self._validate(higher, "higher")
      25         required = self._validate(required, "required")
      26         if higher == required:
      27             return True
      28         visited: set[str] = set()
      29         queue = list(self._rules.get(higher, set()))
      30         while queue:
      31             current = queue.pop()
      32             if current == required:
      33                 return True
      34             if current not in visited:
      35                 visited.add(current)
      36                 queue.extend(self._rules.get(current, set()) - visited)
      37         return False
      38
      39     def __repr__(self) -> str:
      40         return f"SkillHierarchy(rules={self._rules!r})"

