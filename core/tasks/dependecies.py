 from __future__ import annotations
 from collections.abc import Iterable

  class Dependencies:
      """Identifiers of tasks that must be completed before this task may begin.

      Zero or more prerequisite task identifiers. Identifiers are normalized
      (stripped, lowercase) and deduplicated. Immutable after construction.
      """

      __slots__ = ("_deps",)

      def __init__(self, task_ids: Iterable[str] = ()) -> None:
          normalized: set[str] = set()
          for tid in task_ids:
              if not isinstance(tid, str):
                  raise ValueError(f"Task identifier must be a str, got {type(tid).__name__!r}.")
              value = tid.strip().lower()
              if not value:
                  raise ValueError("Task identifier must not be empty or whitespace.")
              normalized.add(value)
          self._deps: frozenset[str] = frozenset(normalized)

      @property
      def task_ids(self) -> frozenset[str]:
          """The immutable set of prerequisite task identifiers."""
          return self._deps

      def depends_on(self, task_id: str) -> bool:
          """Return True if the given task is a direct prerequisite."""
          if not isinstance(task_id, str):
              raise ValueError(f"Task identifier must be a str, got {type(task_id).__name__!r}.")
          return task_id.strip().lower() in self._deps

      def is_empty(self) -> bool:
          """Return True if there are no prerequisite tasks."""
          return not self._deps

      def __eq__(self, other: object) -> bool:
          if isinstance(other, Dependencies):
              return self._deps == other._deps
          return NotImplemented

      def __hash__(self) -> int:
          return hash(self._deps)

      def __repr__(self) -> str:
          return f"Dependencies({set(self._deps)!r})"
