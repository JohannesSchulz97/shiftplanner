class SkillHierarchy:
    def __init__(self) -> None:
        self._rules: dict[str, set[str]] = {}

    @staticmethod
    def _validate(value: str, label: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{label} must not be empty or whitespace")
        return stripped

    def add_rule(self, higher: str, lower: str) -> None:
        higher = self._validate(higher, "higher")
        lower = self._validate(lower, "lower")
        self._rules.setdefault(higher, set()).add(lower)

    def remove_rule(self, higher: str, lower: str) -> None:
        higher = self._validate(higher, "higher")
        lower = self._validate(lower, "lower")
        if higher in self._rules:
            self._rules[higher].discard(lower)

    def can_cover(self, higher: str, required: str) -> bool:
        higher = self._validate(higher, "higher")
        required = self._validate(required, "required")
        if higher == required:
            return True
        visited: set[str] = set()
        queue = list(self._rules.get(higher, set()))
        while queue:
            current = queue.pop()
            if current == required:
                return True
            if current not in visited:
                visited.add(current)
                queue.extend(self._rules.get(current, set()) - visited)
        return False

    def __repr__(self) -> str:
        return f"SkillHierarchy(rules={self._rules!r})"
