LEVEL_ORDER = {"junior": 1, "mid": 2, "senior": 3}


class Person:
    def __init__(self, name):
        self.name = name
        self.skills = {}  # {skill_name: level | None}

    def add_skill(self, skill, level=None):
        if level is not None and level not in LEVEL_ORDER:
            raise ValueError(f"Invalid level '{level}'. Must be one of: {list(LEVEL_ORDER)}")
        if skill not in self.skills:
            self.skills[skill] = level

    def remove_skill(self, skill):
        if skill in self.skills:
            del self.skills[skill]

    def update_skill_level(self, skill, level):
        if skill not in self.skills:
            raise KeyError(f"Skill '{skill}' not found. Add it first.")
        if level is not None and level not in LEVEL_ORDER:
            raise ValueError(f"Invalid level '{level}'. Must be one of: {list(LEVEL_ORDER)}")
        self.skills[skill] = level

    def can_fulfill(self, skill, required_level=None):
        """
        Returns True if this person can fulfill the given skill requirement.

        - If required_level is None, anyone with the skill qualifies.
        - If the person has the skill with no level, they are considered
          capable of fulfilling any level requirement.
        - Otherwise: senior >= mid >= junior (higher fulfills lower).
        """
        if skill not in self.skills:
            return False
        if required_level is None:
            return True
        person_level = self.skills[skill]
        if person_level is None:
            return True
        return LEVEL_ORDER[person_level] >= LEVEL_ORDER[required_level]

    def __repr__(self):
        return f"Person(name={self.name!r}, skills={self.skills})"
