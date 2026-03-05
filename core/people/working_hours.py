      1 class WorkingHours:
       2     """Maximum working hour constraints for a person.
       3
       4     Defines upper bounds on how many hours a person may be assigned,
       5     both within a single day and across an entire planning period
       6     (e.g. a week or schedule cycle).
       7     """
       8
       9     def __init__(self, max_per_day: float, max_per_period: float) -> None:
      10         self.max_per_day = self._validate(max_per_day, "max_per_day")
      11         self.max_per_period = self._validate(max_per_period, "max_per_period")
      12
      13     @staticmethod
      14     def _validate(value: float, label: str) -> float:
      15         if value <= 0:
      16             raise ValueError(f"{label} must be a positive number, got {value}")
      17         return float(value)
      18
      19     def allows_day(self, hours: float) -> bool:
      20         """Return True if the given hours fit within the daily limit."""
      21         return hours <= self.max_per_day
      22
      23     def allows_period(self, hours: float) -> bool:
      24         """Return True if the given hours fit within the planning-period limit."""
      25         return hours <= self.max_per_period
      26
      27     def __repr__(self) -> str:
      28         return f"WorkingHours(max_per_day={self.max_per_day}, max_per_period={self.max_per_period})"

