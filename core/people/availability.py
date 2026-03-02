from enum import Enum


class AvailabilityState(Enum):
    """Represents a person's availability for assignment in a given time slot.

    EXPECTED:     Predefined work shift; assignment is normal and expected.
    OFFERED:      Optional time offered by the person; subject to fairness rules.
    UNAVAILABLE:  Cannot be assigned under any circumstances.
    """

    EXPECTED = "expected"
    OFFERED = "offered"
    UNAVAILABLE = "unavailable"


class Availability:
    def __init__(self) -> None:
        self._slots: dict[str, AvailabilityState] = {}

    @staticmethod
    def _validate(slot: str) -> str:
        stripped = slot.strip()
        if not stripped:
            raise ValueError("slot must not be empty or whitespace")
        return stripped

    def set_state(self, slot: str, state: AvailabilityState) -> None:
        self._slots[self._validate(slot)] = state

    def get_state(self, slot: str) -> AvailabilityState:
        return self._slots.get(self._validate(slot), AvailabilityState.UNAVAILABLE)

    def is_available(self, slot: str) -> bool:
        return self.get_state(slot) in (AvailabilityState.EXPECTED, AvailabilityState.OFFERED)

    def clear(self, slot: str) -> None:
        self._slots.pop(self._validate(slot), None)

    def __repr__(self) -> str:
        return f"Availability(slots={self._slots!r})"
