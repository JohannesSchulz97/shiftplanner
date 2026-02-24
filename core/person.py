class Person:
    def __init__(self, name):
        self.name = name
        self.skills = []

    def add_skill(self, skill):
        if skill not in self.skills:
            self.skills.append(skill)

    def remove_skill(self, skill):
        if skill in self.skills:
            self.skills.remove(skill)

    def __repr__(self):
        return f"Person(name={self.name!r}, skills={self.skills})"
