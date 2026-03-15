# Modeling a workforce scheduler with CP-SAT

**OR-Tools' CP-SAT solver can express every constraint ShiftPlanner needs — overlaps, skills, rest periods, fairness, splittable tasks, and re-solving stability — through a deliberate combination of BoolVars, IntervalVars, enforcement literals, and a carefully tiered objective function.** The modeling choices you make at the variable-design stage ripple through every constraint and objective term, so getting the foundation right matters more than any single constraint pattern. This guide walks through all seven areas with production-ready Python code you can adapt directly, drawing on the CP-SAT Primer (Krupke, TU Braunschweig), Google's official OR-Tools documentation, and patterns from the `shift_scheduling_sat.py` reference example.

---

## 1. Decision variables shape everything downstream

The central modeling decision is how you represent "person P is assigned to work item W during time T." CP-SAT offers three primary variable types, each with distinct trade-offs for a 40-person scheduler.

**The BoolVar matrix** is the workhorse pattern for discrete-slot scheduling. You create one Boolean per (person, task, slot) triple:

```python
from ortools.sat.python import cp_model

model = cp_model.CpModel()

persons = list(range(40))
tasks = ["coverage_A", "coverage_B", "task_X"]
slots = list(range(48))  # e.g., 30-min slots across 24 h

shifts = {}
for p in persons:
    for t in tasks:
        for s in slots:
            shifts[(p, t, s)] = model.new_bool_var(f"shift_p{p}_{t}_s{s}")
```

This produces **P × T × S variables** (40 × 3 × 48 = 5,760 for this example). The Krupke CP-SAT Primer notes that Boolean variables are CP-SAT's native currency — integers are internally encoded via order-encoding into Booleans — so a BoolVar matrix gives the solver maximum propagation leverage. The pattern shines when time is naturally discrete (fixed shift blocks, hourly slots) and constraints are slot-based ("at most one task per person per slot").

**IntVar assignment** collapses one dimension when exactly one person handles a task:

```python
# Direct assignment: which person does task t?
assignment = {}
for t in tasks:
    assignment[t] = model.new_int_var(0, len(persons) - 1, f"who_{t}")
```

This yields only T variables, but channeling to person-level constraints (hours, overlap) requires additional linking variables, often negating the size advantage. Use IntVar assignment for one-to-one matching problems, not for coverage slots where multiple people fill the same role.

**IntervalVar** unlocks CP-SAT's dedicated scheduling propagators — edge-finding, energetic reasoning, and timetabling — which BoolVar sums cannot replicate:

```python
# Per (person, task): optional interval, present only if assigned
assign = {}
start_var = {}
intervals = {}

for p in persons:
    person_intervals = []
    for t, duration in task_durations.items():
        assign[(p, t)] = model.new_bool_var(f"assign_p{p}_{t}")
        start_var[(p, t)] = model.new_int_var(0, horizon - duration, f"start_p{p}_{t}")
        iv = model.new_optional_fixed_size_interval_var(
            start=start_var[(p, t)],
            size=duration,
            is_present=assign[(p, t)],
            name=f"iv_p{p}_{t}",
        )
        person_intervals.append(iv)
        intervals[(p, t)] = iv
    model.add_no_overlap(person_intervals)
```

The `is_present` BoolVar is the key: when it is False, `add_no_overlap` ignores that interval entirely. The Primer warns: *"Do not directly jump to intervals when you have a scheduling problem. Intervals are great if you actually have a somewhat continuous time or space. If you have a more discrete problem, such as a scheduling problem with a fixed number of slots, you can often model this much more efficiently using simple Boolean variables."* For ShiftPlanner, **use BoolVars for coverage slots** (fixed discrete blocks) and **IntervalVars for flexible-start tasks** (continuous time). When both coexist, channel between them: a task's IntervalVar determines its placement, while derived BoolVars for each slot it occupies link into slot-based coverage and hour-counting constraints.

Performance-wise, `new_optional_fixed_size_interval_var` (known duration) is cheaper than `new_optional_interval_var` (variable duration). Keep variable bounds tight — Krupke emphasizes that tight domains improve propagation significantly. For 40 people with ~20 tasks and 48 slots, the BoolVar matrix produces ~38,400 variables; CP-SAT handles this comfortably within seconds on 8 workers.

---

## 2. Seven hard constraints and how to encode each

### No overlapping assignments per person

The interval approach is strongly preferred for continuous-time scheduling because it engages CP-SAT's scheduling propagators:

```python
for p in persons:
    person_intervals = [intervals[(p, t)] for t in tasks]
    model.add_no_overlap(person_intervals)  # one constraint per person
```

For discrete-slot models, the BoolVar sum achieves the same:

```python
for p in persons:
    for s in slots:
        model.add(sum(shifts[(p, t, s)] for t in tasks) <= 1)
```

The interval approach creates **P constraints** with dedicated propagation; the BoolVar approach creates **P × S constraints** with only linear relaxation. For ShiftPlanner's mix of fixed-slot coverage and flexible tasks, use both: intervals with `add_no_overlap` for tasks, BoolVar sums for coverage slots.

### Skill hierarchy: seniors cover junior requirements

Pre-filtering eligible (person, task) pairs at variable-creation time produces the smallest model and fastest solve:

```python
JUNIOR, MID, SENIOR = 1, 2, 3
person_skill = {0: SENIOR, 1: MID, 2: JUNIOR}  # etc.
task_min_skill = {"deploy": SENIOR, "review": MID, "test": JUNIOR}

assign = {}
for p in persons:
    for t, min_level in task_min_skill.items():
        if person_skill[p] >= min_level:  # hierarchy: senior >= mid >= junior
            assign[(p, t)] = model.new_bool_var(f"assign_p{p}_{t}")
```

The alternative — creating all variables and using `model.add(skill_var[p] >= task_min_skill[t]).only_enforce_if(assign[(p, t)])` — is more declarative but produces variables the solver must reason about even when they can never be True. Krupke notes that enforcement literals weaken the linear relaxation. **Pre-filtering is the right default** when skills are static input data.

### Resource exclusivity

A shared room or piece of equipment can serve only one person at a time. With IntervalVars, collect all optional intervals that use the resource and apply a single `add_no_overlap`:

```python
resource_intervals = {r: [] for r in resources}
for p in persons:
    for t, (dur, res) in task_resource.items():
        iv = model.new_optional_fixed_size_interval_var(
            start=start_var[(p, t)], size=dur,
            is_present=assign[(p, t)], name=f"iv_{res}_p{p}_t{t}",
        )
        resource_intervals[res].append(iv)

for res in resources:
    model.add_no_overlap(resource_intervals[res])
```

### Maximum working hours per day and per period

With BoolVar assignments where each task has a known duration, hours tracking is a weighted sum:

```python
MAX_DAILY = 10
MAX_PERIOD = 40

for p in persons:
    # Per-day cap
    for day in range(num_days):
        day_tasks = [(tid, dur) for tid, (d, dur) in task_data.items() if d == day]
        model.add(sum(assign[(p, tid)] * dur for tid, dur in day_tasks) <= MAX_DAILY)
    # Per-period cap
    model.add(
        sum(assign[(p, tid)] * task_data[tid][1] for tid in task_data) <= MAX_PERIOD
    )
```

### Minimum rest period between shifts

The elegant interval-based approach appends a mandatory rest interval after each work interval:

```python
REST_HOURS = 11

for p in persons:
    person_intervals = []
    for s in all_shifts:
        presence = assign[p, s]
        start = model.new_int_var(earliest, latest, f"start_p{p}_s{s}")
        work_iv = model.new_optional_fixed_size_interval_var(
            start=start, size=duration,
            is_present=presence, name=f"work_p{p}_s{s}",
        )
        rest_iv = model.new_optional_fixed_size_interval_var(
            start=start + duration, size=REST_HOURS,
            is_present=presence, name=f"rest_p{p}_s{s}",
        )
        person_intervals.extend([work_iv, rest_iv])
    model.add_no_overlap(person_intervals)
```

Because `add_no_overlap` ignores absent intervals, the rest interval only activates when the person is actually assigned. This avoids O(n²) pairwise gap constraints and leverages the scheduling propagator directly.

### Team size and coverage

```python
for task, (min_team, max_team) in task_requirements.items():
    for t in time_periods:
        headcount = sum(assign[(p, task, t)] for p in persons)
        model.add(headcount >= min_team)
        model.add(headcount <= max_team)

# Exact coverage: 3 physicians during period 0
model.add(sum(assign[(p, task, 0)] for p in physicians for task in their_tasks) == 3)
```

### Task dependencies across people

Precedence constraints with IntervalVars are the cleanest pattern — they work regardless of who performs each task:

```python
dependencies = [("inspection", "assessment"), ("assessment", "briefing")]
for pred, succ in dependencies:
    model.add(task_starts[succ] >= task_ends[pred])
```

This single linear constraint per dependency edge is all CP-SAT needs. Combined with per-person `add_no_overlap` using optional intervals, this gives you a full job-shop-style scheduling backbone.

---

## 3. Soft constraints demand careful objective architecture

The canonical soft-constraint pattern uses a violation BoolVar with full reification to ensure the solver accurately accounts for every penalty:

```python
penalty_vars = []  # (var, weight, category, name)

for s in required_slots:
    uncovered = model.new_bool_var(f"uncov_req_{s}")
    slot_sum = sum(shifts[(p, s)] for p in eligible_persons)
    # Full reification: uncovered==1 IFF slot has zero coverage
    model.add(slot_sum >= 1).only_enforce_if(uncovered.negated())
    model.add(slot_sum == 0).only_enforce_if(uncovered)
    penalty_vars.append((uncovered, 1_000_000, "required_coverage", f"slot_{s}"))

model.minimize(sum(var * weight for var, weight, _, _ in penalty_vars))
```

**Weight engineering for strict tier dominance** requires that each tier's weight exceeds the maximum possible total penalty from all lower tiers combined:

```python
# Compute exact bounds bottom-up:
MAX_T4 = 40 * 100   # max travel/preference violations
MAX_T3 = 40          # fairness (one per person)
MAX_T2 = 100         # optional coverage slots

W4 = 1
W3 = MAX_T4 * W4 + 1          #     4,001
W2 = MAX_T3 * W3 + 1          #   160,041
W1 = MAX_T2 * W2 + 1          # 16,004,101

# Max objective ≈ 1.6 billion — safely within int64 (max 9.2 × 10^18)
```

**Lexicographic multi-pass solving** is the cleaner alternative when you have 4+ tiers or want exact priority guarantees:

```python
def solve_lexicographic(model, tier_objectives, tier_order, time_per_pass=60.0):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_per_pass
    results = {}

    for tier in tier_order:
        model.minimize(tier_objectives[tier])
        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        tier_val = int(solver.objective_value)
        results[tier] = tier_val
        # Fix this tier's result with 5% relaxation (Krupke's recommendation)
        model.add(tier_objectives[tier] <= int(tier_val * 1.05) if tier_val > 0 else 0)
    return results
```

The trade-off: multi-pass requires N solves (2–4× slower for 4 tiers) but gives exact tier separation. The Primer recommends **5% relaxation** on earlier tiers to avoid over-constraining later passes.

For debugging, a `PenaltyTracker` class that logs per-category breakdowns is invaluable:

```python
class PenaltyTracker:
    def __init__(self):
        self.terms = {}  # category -> [(var, weight, name)]

    def add(self, category, var, weight, name=""):
        self.terms.setdefault(category, []).append((var, weight, name))

    def build_objective(self, model):
        model.minimize(sum(v * w for cat in self.terms.values() for v, w, _ in cat))

    def report(self, solver):
        for cat, entries in sorted(self.terms.items()):
            active = sum(1 for v, _, _ in entries if solver.value(v) > 0)
            cost = sum(solver.value(v) * w for v, w, _ in entries)
            print(f"  {cat:30s}: {active}/{len(entries)} active, cost={cost:>12d}")
```

---

## 4. Fairness through cross-multiplication avoids floating point entirely

The fairness goal — equalizing `assigned[p] / offered[p]` across all people — requires integer reformulation since **CP-SAT has no floating-point variables**. Cross-multiplication is the key insight: comparing ratios `a/b` vs `c/d` becomes `a*d` vs `c*b`, which is purely linear.

### Minimax deviation: the recommended default

This minimizes the worst-case unfairness and is **fully linear** — no `add_multiplication_equality` needed:

```python
offered = {0: 10, 1: 8, 2: 15, 3: 5, 4: 12}  # slots volunteered
people = list(offered.keys())
total_offered = sum(offered.values())  # constant: 50

assigned = {}
for p in people:
    assigned[p] = model.new_int_var(0, offered[p], f"assigned_{p}")
    # ... linked to sum of assignment BoolVars

total_assigned = model.new_int_var(0, total_offered, "total_assigned")
model.add(total_assigned == sum(assigned[p] for p in people))

# Cross-multiplied deviation from average ratio:
# diff[p] = assigned[p] * total_offered - total_assigned * offered[p]
# Both total_offered and offered[p] are CONSTANTS, so this is LINEAR
D = model.new_int_var(0, total_offered, "max_deviation")

for p in people:
    ub = offered[p] * total_offered
    lb = -sum(offered.values()) * offered[p]
    diff_p = model.new_int_var(lb, ub, f"diff_{p}")
    model.add(diff_p == assigned[p] * total_offered - total_assigned * offered[p])
    model.add(diff_p <= D * offered[p])     # upper bound
    model.add(-diff_p <= D * offered[p])    # lower bound (absolute value)

model.minimize(D)
```

This adds only **P + 1 IntVars and 3P constraints** — trivial overhead for 40 people.

### Max-min fairness: raise the worst-off person

```python
SCALE = 1000  # milliratio precision
z = model.new_int_var(0, SCALE, "min_ratio_scaled")

for p in people:
    # z <= assigned[p] * SCALE / offered[p], cross-multiplied:
    model.add(z * offered[p] <= assigned[p] * SCALE)

model.maximize(z)
```

This is also fully linear and fast, but it focuses only on the worst-off person. People above the floor may have widely varying ratios.

### Sum of squared deviations: smoothest but costliest

```python
squared_devs = []
for p in people:
    diff_p = model.new_int_var(-8000, 8000, f"diff_{p}")
    model.add(diff_p == assigned[p] * total_offered - total_assigned * offered[p])
    sq_p = model.new_int_var(0, 64_000_000, f"sq_{p}")
    model.add_multiplication_equality(sq_p, [diff_p, diff_p])
    squared_devs.append(sq_p)

model.minimize(sum(squared_devs))
```

`add_multiplication_equality` is **significantly more resource-intensive** than linear constraints (Krupke). For 40 people, the 40 multiplication constraints are manageable but expect **2–3× longer solve times** versus the linear minimax approach. The squared formulation penalizes all deviations proportionally, producing the smoothest distribution.

**The practical recommendation**: start with minimax deviation as your default. For a two-level guarantee, use max-min as a Tier 3 lexicographic objective and minimax deviation as Tier 4 to break ties.

---

## 5. Splittable tasks need multiple optional intervals summing to a total

A **non-splittable task** is a single IntervalVar with fixed size — the solver places it as one continuous block. Splittable tasks require a different pattern: create multiple optional sub-intervals whose sizes sum to the total required duration.

```python
task_total_duration = 8  # hours total
max_fragments = 4  # allow splitting into up to 4 pieces

fragments = []
frag_sizes = []

for f in range(max_fragments):
    is_used = model.new_bool_var(f"task_frag_{f}_used")
    size = model.new_int_var(0, task_total_duration, f"task_frag_{f}_size")
    start = model.new_int_var(0, horizon, f"task_frag_{f}_start")
    end = model.new_int_var(0, horizon, f"task_frag_{f}_end")

    interval = model.new_optional_interval_var(
        start=start, size=size, end=end,
        is_present=is_used, name=f"task_frag_{f}",
    )
    # If not used, size must be 0
    model.add(size == 0).only_enforce_if(is_used.negated())
    model.add(size >= 1).only_enforce_if(is_used)  # minimum fragment size

    fragments.append(interval)
    frag_sizes.append(size)

# Total duration constraint: fragments must sum to required hours
model.add(sum(frag_sizes) == task_total_duration)

# Add fragments to per-person no_overlap
# (assuming all fragments are assigned to the same person)
model.add_no_overlap(person_intervals + fragments)
```

For **non-splittable enforcement**, simply use a single `new_fixed_size_interval_var` — the fixed size prevents splitting by construction. Alternatively, if you want a toggle between splittable and non-splittable for the same task:

```python
# Force non-splittability: only one fragment can be active
is_nonsplittable = model.new_bool_var("task_nonsplittable")
model.add(sum(is_used[f] for f in range(max_fragments)) == 1).only_enforce_if(is_nonsplittable)
```

Splittable task fragments interact naturally with working-hours constraints — just include their sizes in the daily and period hour sums. Each fragment also participates in the per-person `add_no_overlap`, so the solver automatically prevents a person from working two fragments simultaneously.

---

## 6. Re-solving preserves schedule trust through hints, pins, and stability penalties

When a change occurs after publishing a schedule (someone calls in sick, a new task appears), ShiftPlanner must re-solve while minimizing disruption. Three mechanisms work together.

### Solution hints guide without constraining

```python
# After initial solve, extract and persist the solution
prev_solution = {key: solver.value(var) for key, var in work.items()}

# On re-solve with a modified model:
for key, var in new_work_vars.items():
    if key in prev_solution:
        model.add_hint(var, prev_solution[key])

solver.parameters.repair_hint = True  # attempt to fix infeasible hints
```

Hints tell CP-SAT which values to try first during branching — one search worker follows the hint while others explore independently. A complete, feasible hint triggers the log message *"The solution hint is complete and is feasible"* and typically produces a good first solution within milliseconds. **Key pitfall**: if presolve consumes the entire time limit (large models), the hint may never be used and status returns `UNKNOWN`. Always allocate sufficient time beyond presolve.

### Hard and soft pinning

Lock past days with equality constraints; allow future changes with stability penalties:

```python
CURRENT_DAY = 3  # Wednesday — Mon-Tue are locked

for (p, d, s), var in work.items():
    if d < CURRENT_DAY:
        # Hard pin: cannot change published past
        model.add(var == prev_solution[(p, d, s)])
    else:
        # Soft stability penalty: discourage changes
        old_val = prev_solution[(p, d, s)]
        changed = model.new_bool_var(f"changed_{p}_{d}_{s}")
        if old_val == 1:
            model.add(changed + var == 1)  # changed=1 iff var flipped to 0
        else:
            model.add(changed == var)       # changed=1 iff var flipped to 1
        # Add to objective with appropriate weight
        stability_penalties.append(changed * STABILITY_WEIGHT)
```

**Calibrating stability weight**: if the primary objective costs 1 unit per uncovered slot, a `STABILITY_WEIGHT` of 5–20 means "changing one assignment is as bad as 5–20 uncovered slots." Start at 10 and tune. Consider time-decaying weights — changes closer to today cost more.

### Serialization for persistence

```python
import json
from pathlib import Path

def save_solution(solution, path):
    serializable = {f"{p}|{d}|{s}": v for (p, d, s), v in solution.items()}
    Path(path).write_text(json.dumps(serializable))

def load_solution(path):
    raw = json.loads(Path(path).read_text())
    return {(parts[0], int(parts[1]), parts[2]): v
            for key, v in raw.items()
            for parts in [key.split("|")]}
```

---

## 7. Enforcement literals let you toggle constraints without rebuilding

`only_enforce_if` implements **half-reification**: when the literal is True the constraint must hold; when False, it is ignored entirely (not violated — just absent).

```python
alice_available = model.new_bool_var("alice_available_day3")

# This constraint only activates when Alice is unavailable
model.add(work[("Alice", 3, "Off")] == 1).only_enforce_if(~alice_available)
```

**Constraint groups** share a single control literal:

```python
weekend_rules = model.new_bool_var("weekend_overtime_rules")
for p in persons:
    for d in weekend_days:
        model.add(
            sum(work[(p, d, s)] for s in non_off_shifts) <= 1
        ).only_enforce_if(weekend_rules)
# Toggle: model.add(weekend_rules == 0) disables all weekend rules
```

**What-if queries** use `model.clone()` (available since OR-Tools ~v9.8) to test hypotheticals without touching the base model:

```python
class WhatIfEngine:
    def __init__(self, base_model, work_vars):
        self.base_model = base_model
        self.work_vars = work_vars

    def test_unavailability(self, person, day):
        test_model = self.base_model.clone()
        var = self.work_vars[(person, day, "Off")]
        clone_var = test_model.get_bool_var_from_proto_index(var.index)
        test_model.add(clone_var == 1)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 15
        status = solver.solve(test_model)
        return {
            "feasible": status in (cp_model.OPTIMAL, cp_model.FEASIBLE),
            "objective": solver.objective_value if status != cp_model.INFEASIBLE else None,
        }
```

For lighter-weight what-if probes, `model.add_assumptions([literal1, literal2])` temporarily fixes Boolean values for a single solve without adding permanent constraints. Assumptions also support **UNSAT core extraction** via `solver.sufficient_assumptions_for_infeasibility()`, which is invaluable for explaining *why* a schedule is infeasible.

### What supports `only_enforce_if` and what does not

This is a critical gotcha. **Supported**: `model.add()` (all linear constraints), `add_bool_or`, `add_bool_and`, and optional intervals (via `is_present`). **Not supported**: `add_no_overlap`, `add_cumulative`, `add_all_different`, `add_circuit`, `add_element`, `add_min_equality`, `add_max_equality`, `add_multiplication_equality`, `add_allowed_assignments`. For unsupported constraints, the workaround is decomposition into linear constraints or using optional intervals. Krupke also warns that enforcement literals *"are often not very good for the linear relaxation"* — adding redundant convex-hull constraints can help the solver's LP bound.

---

## Conclusion

ShiftPlanner's modeling strategy should follow a clear hierarchy. **Use BoolVars for discrete coverage slots** and **IntervalVars for flexible-start tasks** — mixing both in one model is not just acceptable but optimal. Pre-filter impossible assignments (skill hierarchy, availability) at variable-creation time rather than adding enforcement constraints post-hoc; this produces the smallest model with the strongest propagation. For the objective, start with weighted-sum penalty tiers using the exact dominance formula (`W_k = max_violations_below * W_{k-1} + 1`), and graduate to lexicographic multi-pass if you exceed 5 tiers or need exact priority guarantees. The minimax deviation fairness formulation is fully linear and adds negligible overhead for 40 people — use it as the default over sum-of-squares unless distribution smoothness is paramount. For re-solving, the three-layer defense of hints + hard pins + soft stability penalties keeps published schedules stable while allowing necessary changes. And enforcement literals plus `model.clone()` give the AI assistant layer the ability to answer "what if" questions in under 15 seconds without ever modifying the production model.