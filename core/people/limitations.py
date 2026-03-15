       1 class Limitations:
       2     """Explicit exclusions that prevent a person from performing certain assignments.
       3
       4     Limitations are independent of availability — they represent hard constraints
       5     (e.g. legal restrictions, certifications, conflicts) that block assignment
       6     regardless of whether the person is otherwise available.
       7     """
       8
       9     def __init__(self) -> None:
      10         self._limitations: set[str] = set()
      11
      12     @staticmethod
      13     def _validate(value: str) -> str:
      14         stripped = value.strip()
      15         if not stripped:
      16             raise ValueError("limitation must not be empty or whitespace")
      17         return stripped
      18
      19     def add(self, limitation: str) -> None:
      20         """Add a limitation by identifier. Duplicates are ignored."""
      21         self._limitations.add(self._validate(limitation))
      22
      23     def remove(self, limitation: str) -> None:
      24         """Remove a limitation. Silent no-op if not present."""
      25         self._limitations.discard(self._validate(limitation))
      26
      27     def has(self, limitation: str) -> bool:
      28         """Return True if the given limitation is active."""
      29         return self._validate(limitation) in self._limitations
      30
      31     def __repr__(self) -> str:
      32         return f"Limitations(limitations={self._limitations!r})"class Limitations:
    
