from __future__ import annotations

from core.schedule.assignment import Assignment


def _skill_satisfied(
    required_skill: str,
    person_skills: set[str],
    skill_hierarchy: dict[str, set[str]],
) -> bool:
    """Return True if the person holds the required skill directly or via hierarchy.

    skill_hierarchy maps a higher skill to the set of lower skills it covers.
    A required skill is satisfied if the person holds it exactly, or holds a
    higher skill that transitively covers it.
    """
    if required_skill in person_skills:
        return True
    for held_skill in person_skills:
        covered = skill_hierarchy.get(held_skill, set())
        if required_skill in covered:
            return True
    return False


def validate_skill_matching(
    assignments: list[Assignment],
    person_skills: dict[str, set[str]],
    skill_hierarchy: dict[str, set[str]],
    required_skills: dict[str, set[str]],
) -> None:
    """Enforce the hard constraint that assigned persons hold all required skills.

    For each assignment, every required skill must be satisfied by the person's
    own skills or by a higher skill they hold that covers it via the hierarchy.
    Raises ValueError on the first unsatisfied skill found.

    Args:
        assignments:     List of assignments to validate.
        person_skills:   Maps person_id → set of skill identifiers they hold.
        skill_hierarchy: Maps higher_skill → set of lower skills it covers.
        required_skills: Maps assignment_id → set of required skill identifiers.
    """
    for assignment in assignments:
        person_id = assignment.person_id
        assignment_id = assignment.assignment_id
        skills = person_skills.get(person_id, set())
        needed = required_skills.get(assignment_id, set())

        for skill in needed:
            if not _skill_satisfied(skill, skills, skill_hierarchy):
                raise ValueError(
                    f"Person {person_id!r} lacks required skill {skill!r} "
                    f"for assignment {assignment_id!r}."
                )
