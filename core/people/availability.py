       1 +from enum import Enum
       2 +
       3 +
       4 +class AvailabilityState(Enum):
       5 +    """Represents a person's availability for assignment in a given time slot.
       6 +
       7 +    EXPECTED:     Predefined work shift; assignment is normal and expected.
       8 +    OFFERED:      Optional time offered by the person; subject to fairness rules.
       9 +    UNAVAILABLE:  Cannot be assigned under any circumstances.
      10 +    """
      11 +
      12 +    EXPECTED = "expected"
      13 +    OFFERED = "offered"
      14 +    UNAVAILABLE = "unavailable"
      15 +
      16 +
      17 +class Availability:
      18 +    def __init__(self) -> None:
      19 +        self._slots: dict[str, AvailabilityState] = {}
      20 +
      21 +    @staticmethod
      22 +    def _validate(slot: str) -> str:
      23 +        stripped = slot.strip()
      24 +        if not stripped:
      25 +            raise ValueError("slot must not be empty or whitespace")
      26 +        return stripped
      27 +
      28 +    def set_state(self, slot: str, state: AvailabilityState) -> None:
      29 +        self._slots[self._validate(slot)] = state
      30 +
      31 +    def get_state(self, slot: str) -> AvailabilityState:
      32 +        return self._slots.get(self._validate(slot), AvailabilityState.UNAVAILABLE)
      33 +
      34 +    def is_available(self, slot: str) -> bool:
      35 +        return self.get_state(slot) in (AvailabilityState.EXPECTED, AvailabilityState.OFFERED)
      36 +
      37 +    def clear(self, slot: str) -> None:
      38 +        self._slots.pop(self._validate(slot), None)
      39 +
      40 +    def __repr__(self) -> str:
      41 +        return f"Availability(slots={self._slots!r})"
