class CoverageRequirement:
    """An abstract staffing demand tied to a specific shift.

    Defines how many people with a given skill are needed during a given shift,
    independent of any specific named task. Coverage Requirements and Tasks
    coexist in the same planning cycle and compete for the same pool of people.
    """

    def __init__(self, shift_name: str, required_skill: str, count: int) -> None:
        self.shift_name = self._validate_str(shift_name, "shift_name")
        self.required_skill = self._validate_str(required_skill, "required_skill")
        self.count = self._validate_count(count)

    @staticmethod
    def _validate_str(value: str, label: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{label} must not be empty or whitespace")
        return stripped

    @staticmethod
    def _validate_count(count: int) -> int:
        if count < 1:
            raise ValueError(f"count must be at least 1, got {count}")
        return count

    def __repr__(self) -> str:
        return (
            f"CoverageRequirement(shift_name={self.shift_name!r}, "
            f"required_skill={self.required_skill!r}, count={self.count})"
        )
