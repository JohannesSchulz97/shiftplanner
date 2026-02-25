class Person:
    def __init__(self, name):
        self.name = name
        self.skills = set()

    def add_skill(self, skill):
        self.skills.add(skill)

    def remove_skill(self, skill):
        self.skills.discard(skill)

    def has_skill(self, skill):
        return skill in self.skills

    def __repr__(self):
        return f"Person(name={self.name!r}, skills={self.skills})"
