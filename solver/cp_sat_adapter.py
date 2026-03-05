from ortools.sat.python import cp_model
from typing import Dict


class CpSatAdapter:
    """
    Thin wrapper around OR-Tools CP-SAT.
    Keeps CP-SAT isolated from domain/solver orchestration.
    """

    def __init__(self) -> None:
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.assignment_vars: Dict[str, cp_model.IntVar] = {}

    def create_bool_var(self, name: str) -> cp_model.IntVar:
        return self.model.NewBoolVar(name)

    def create_assignment_var(self, person_id: str, assignment_id: str, shift_id: str) -> cp_model.IntVar:
        var_name = f"{person_id}__{assignment_id}__{shift_id}"
        v = self.model.NewBoolVar(var_name)
        self.assignment_vars[var_name] = v
        return v

    def get_all_assignment_vars(self) -> Dict[str, cp_model.IntVar]:
        return self.assignment_vars

    def solve(self) -> int:
        return self.solver.Solve(self.model)

    def get_value(self, var: cp_model.IntVar) -> int:
        return int(self.solver.Value(var))
