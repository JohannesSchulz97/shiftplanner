    1 class RestPeriod:
       2     """Minimum required rest time between two consecutive assignments for a person.
       3
       4     Enforces a mandatory gap (in hours) between the end of one assignment
       5     and the start of the next, ensuring legal or contractual rest requirements
       6     are respected during scheduling.
       7     """
       8
       9     def __init__(self, minimum_hours: float) -> None:
      10         self.minimum_hours = self._validate(minimum_hours)
      11
      12     @staticmethod
      13     def _validate(value: float) -> float:
      14         if value <= 0:
      15             raise ValueError(f"minimum_hours must be a positive number, got {value}")
      16         return float(value)
      17
      18     def allows_gap(self, hours_between: float) -> bool:
      19         """Return True if the gap between assignments meets the minimum rest requirement."""
      20         return hours_between >= self.minimum_hours
      21
      22     def required_gap(self) -> float:
      23         """Return the configured minimum rest hours."""
      24         return self.minimum_hours
      25
      26     def __repr__(self) -> str:
      27         return f"RestPeriod(minimum_hours={self.minimum_hours})"
