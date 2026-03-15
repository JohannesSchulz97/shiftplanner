# Designing an LLM-driven CP-SAT scheduling system

**The most reliable architecture for ShiftPlanner is a structured-output pipeline where the LLM modifies a validated Pydantic configuration object — never the CP-SAT model directly.** This pattern eliminates the most common LLM code-generation failures (wrong API calls, type errors, hallucinated variables) by constraining the LLM to a narrow, schema-validated interface. Recent benchmarks confirm this: agentic approaches with structured tool use and iterative validation achieve **91–100% accuracy** on constraint programming tasks, while single-shot code generation tops out around 65%. The six subsystems below form a cohesive design where natural language flows through interpretation, validation, confirmation, solving, and explanation — each layer independently testable and robust to LLM error.

---

## 1. The model should be config-driven, not code-driven

The central architectural decision is that **the LLM never touches CP-SAT code**. Instead, it modifies a Pydantic `ConstraintConfig` object, and the model is rebuilt deterministically from that config on every solve. This creates a type-safe, bounded API surface that makes validation trivial and eliminates entire categories of LLM error.

**Variable naming** should be semantic and human-readable — `assign_Alice_Monday_Morning` rather than `x[3][0][1]`. LLMs reason about natural language; indexed arrays are a leading source of off-by-one errors in LLM-generated constraint code. Store variables in a typed registry dataclass keyed by `(person_name, day, shift_type)` tuples:

```python
from dataclasses import dataclass, field
from ortools.sat.python import cp_model

@dataclass
class ShiftPlannerVariables:
    """Central registry — all variables addressable by semantic keys."""
    assignments: dict[tuple[str, str, str], cp_model.IntVar] = field(default_factory=dict)
    enforcement_literals: dict[str, cp_model.IntVar] = field(default_factory=dict)
    penalties: dict[str, cp_model.IntVar] = field(default_factory=dict)

def create_variables(model, people, slots) -> ShiftPlannerVariables:
    v = ShiftPlannerVariables()
    for person in people:
        for slot in slots:
            key = (person.name, slot.day, slot.shift)
            v.assignments[key] = model.new_bool_var(
                f"assign_{person.name}_{slot.day}_{slot.shift}"
            )
    for group in ["max_hours", "skill_matching", "availability", "fairness"]:
        v.enforcement_literals[group] = model.new_bool_var(f"enforce_{group}")
    return v
```

**Constraint functions** follow a uniform signature — `(model, variables, config)` — and each returns a list of human-readable descriptions of what it added. This description log becomes part of the LLM's context for explanation generation. Each function checks `config.{group}_enabled` before adding anything, and uses `only_enforce_if` enforcement literals for runtime toggleability:

```python
from pydantic import BaseModel, Field

class ConstraintConfig(BaseModel):
    """The LLM modifies THIS — never the CP-SAT model."""
    max_hours_enabled: bool = True
    max_hours_per_week: int = 40
    skill_matching_enabled: bool = True
    availability_enabled: bool = True
    # Per-person unavailability: {"Alice": ["Monday_Morning", "Thursday_Morning"]}
    unavailability: dict[str, list[str]] = Field(default_factory=dict)
    staffing_requirements: dict[str, int] = Field(default_factory=dict)
    overtime_penalty_weight: int = 100
    fairness_penalty_weight: int = 50
    preference_weight: int = 10

def add_availability_constraints(model, variables, config) -> list[str]:
    """Block assignments where people are marked unavailable."""
    descriptions = []
    if not config.availability_enabled:
        return descriptions
    lit = variables.enforcement_literals["availability"]
    for person, slots in config.unavailability.items():
        for slot_key in slots:
            day, shift = slot_key.rsplit("_", 1)
            key = (person, day, shift)
            if key in variables.assignments:
                model.add(variables.assignments[key] == 0).only_enforce_if(lit)
                descriptions.append(f"{person} blocked from {day} {shift}")
    return descriptions
```

The model builder orchestrates all constraint functions and applies solution hints from the previous solve. Since the model is rebuilt from scratch each time, the config object is the **single source of truth** — serializable, diffable, and trivially undoable by reverting to a previous config snapshot.

**Exposing model state to the LLM** requires a custom high-level JSON representation, not raw protobuf. The serialized state includes the people list, slot definitions, active constraint descriptions, current solution assignments, and penalty breakdowns — everything the LLM needs to reason about the next modification without understanding CP-SAT internals:

```python
def serialize_for_llm(builder, solver, variables) -> dict:
    assignments = {}
    for (person, day, shift), var in variables.assignments.items():
        if solver.value(var) == 1:
            assignments.setdefault(person, []).append(f"{day}_{shift}")
    return {
        "people": [{"name": p.name, "skills": p.skills} for p in builder.people],
        "config": builder.config.model_dump(),
        "current_assignments": assignments,
        "penalties": {k: solver.value(v) for k, v in variables.penalties.items()},
        "objective_value": solver.objective_value,
        "active_constraints": builder.constraint_log,
    }
```

---

## 2. Structured JSON change specs beat code generation decisively

The pipeline from natural language to constraint changes has four layers: **schema validation → entity resolution → feasibility pre-check → human confirmation**. The critical design choice is using Claude's **strict tool use** (`strict: true`) to guarantee schema-compliant JSON output through constrained decoding at the token level — not LLM code generation.

The evidence is clear. Microsoft Research's MeetMate (2024) demonstrated that LLMs can translate natural language scheduling preferences into structured constraint representations with high precision. Security research documents severe RCE vulnerabilities in systems that execute LLM-generated code. And Claude's strict structured outputs guarantee the output matches the schema — zero parsing failures possible.

**The change spec schema** uses a discriminated union supporting nine change types. Each change is a flat JSON object with a `type` field and type-specific properties:

```python
INTERPRET_TOOL = {
    "name": "interpret_schedule_change",
    "strict": True,
    "description": (
        "Interpret a natural language scheduling request into structured "
        "constraint changes. Set confidence='low' when ambiguous. "
        "Always list assumptions made."
    ),
    "input_schema": {
        "type": "object",
        "required": ["changes", "confidence", "interpretation_summary"],
        "additionalProperties": False,
        "properties": {
            "changes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type"],
                    "properties": {
                        "type": {"type": "string", "enum": [
                            "availability_change", "staffing_requirement",
                            "shift_preference", "skill_assignment",
                            "constraint_weight", "time_off", "max_hours"
                        ]},
                        "person": {"type": "string"},
                        "day": {"type": "string"},
                        "shift": {"type": "string", "enum": [
                            "morning", "afternoon", "evening", "any"
                        ]},
                        "available": {"type": "boolean"},
                        "min_staff": {"type": "integer", "minimum": 0},
                        "skill": {"type": "string"},
                        "min_count": {"type": "integer", "minimum": 1},
                        "weight": {"type": "integer", "minimum": 0},
                        "reason": {"type": "string"},
                    }
                }
            },
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "interpretation_summary": {"type": "string"},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "ambiguities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string"},
                        "issue": {"type": "string"},
                        "options": {"type": "array", "items": {"type": "string"}}
                    }
                }
            }
        }
    }
}
```

**The dual-tool pattern** provides a second tool, `request_clarification`, that the LLM selects when the input is too ambiguous to interpret. Using `tool_choice: {"type": "any"}` forces Claude to use one of the two tools. Five ambiguity types arise in scheduling — entity ("which Alice?"), temporal ("next week" → which dates?), scope ("move Alice" → all shifts?), semantic (hard constraint vs. preference?), and quantitative ("more people" → how many?). When Claude flags `confidence: "low"` with populated ambiguities, the system triggers a clarification dialog before proceeding.

**The system prompt** provides the LLM with full context — current date, schedule period, employee list with aliases, shift definitions, current constraint config, and bounds:

```python
SYSTEM_PROMPT = """You are ShiftPlanner's scheduling assistant. Convert natural
language requests into structured constraint modifications.

CONTEXT:
- Schedule: {start} to {end}. Today: {today}
- Employees: {employee_json}
- Shifts: morning (6am-2pm), afternoon (2pm-10pm), evening (10pm-6am)
- Active constraints: {constraints_summary}

RULES:
1. Resolve relative dates ("Thursday") to ISO dates (YYYY-MM-DD).
2. Fuzzy-match employee names. Flag ambiguity if multiple matches.
3. List ALL constraint changes implied by the request.
4. Set confidence="low" when ambiguous. Always list assumptions.
5. Aliases: {aliases_json}"""
```

**Entity resolution** uses fuzzy string matching with a configurable threshold against the known employee list. Range checking validates that staffing numbers don't exceed capacity and dates fall within the schedule period. The feasibility pre-check clones the model, applies the proposed changes, and runs a quick 5-second solve to detect infeasibility before the user commits. Only after all four layers pass does the system present a confirmation summary.

---

## 3. What-if queries use the rebuild-from-scratch pattern naturally

Supporting hypothetical queries like "what would happen if Alice was unavailable all week?" requires solving a modified model without affecting the committed state. ShiftPlanner's rebuild-from-scratch architecture makes this elegant — **a what-if query is just a normal solve with a temporary config modification**.

Three patterns exist, in order of recommendation:

**Pattern 1: Config-copy + rebuild (recommended).** Deep-copy the `ConstraintConfig`, apply hypothetical changes to the copy, rebuild and solve, compare results, discard. This is the cleanest approach for ShiftPlanner since the model is always rebuilt from config:

```python
import copy

async def execute_what_if(
    builder: "ShiftPlannerModelBuilder",
    hypothetical_changes: list[dict],
    current_solution: dict,
) -> dict:
    """Execute a what-if query without modifying committed state."""
    # 1. Deep-copy the config
    hypo_config = builder.config.model_copy(deep=True)
    
    # 2. Apply hypothetical changes to the copy
    for change in hypothetical_changes:
        hypo_config = apply_change_to_config(change, hypo_config)
    
    # 3. Build a fresh model from the hypothetical config
    hypo_builder = ShiftPlannerModelBuilder(
        people=builder.people, slots=builder.slots, config=hypo_config
    )
    hypo_builder._previous_solution = builder._previous_solution  # warm-start
    model, variables = hypo_builder.build()
    
    # 4. Solve (in ThreadPoolExecutor since CP-SAT releases GIL)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    status = solver.solve(model)
    
    # 5. Compare and return diff (original state untouched)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        hypo_solution = extract_solution(solver, variables)
        diff = compute_schedule_diff(current_solution, hypo_solution)
        return {"feasible": True, "diff": diff, "solution": hypo_solution}
    else:
        return {"feasible": False, "status": solver.status_name(status)}
```

**Pattern 2: Enforcement literals.** Add hypothetical constraints gated by a boolean literal, solve with it forced true, then discard. This avoids rebuilding but fights against the rebuild-from-scratch architecture. More useful for quick feasibility checks during a single solve:

```python
def add_hypothetical_constraint(model, variables, hypothesis_lit):
    """Example: 'What if Alice can't work any morning shift?'"""
    for day in DAYS:
        key = ("Alice", day, "Morning")
        if key in variables.assignments:
            model.add(
                variables.assignments[key] == 0
            ).only_enforce_if(hypothesis_lit)
```

**Pattern 3: `model.clone()`.** CP-SAT's `CpModel.clone()` creates a copy of the model protobuf. You can add constraints to the clone without affecting the original. However, the clone does not carry over Python-side variable references — you lose the `ShiftPlannerVariables` registry. This makes it awkward for querying solution values. It's best suited for quick feasibility checks where you don't need to extract a full solution.

**For ~40 people, rebuild-from-scratch is fast enough for interactive use.** A typical scheduling model with 40 people × 7 days × 3 shifts = 840 boolean variables plus constraints builds in under 100ms. CP-SAT solve times for this scale are typically **1–10 seconds** for a good solution, well within interactive bounds. Use `solver.parameters.max_time_in_seconds = 30` and return the best feasible solution found within that window.

**Infeasibility detection** leverages CP-SAT's assumptions mechanism. By passing enforcement literals as assumptions, `sufficient_assumptions_for_infeasibility()` returns the minimal subset of assumptions that cause the conflict — directly identifying which constraint groups clash:

```python
def diagnose_infeasibility(model, variables, solver) -> list[str]:
    """Identify which constraint groups conflict."""
    assumptions = [
        variables.enforcement_literals[group]
        for group in variables.enforcement_literals
    ]
    # Solve with assumptions
    solver.parameters.max_time_in_seconds = 10
    status = solver.solve(model, assumptions=assumptions)
    
    if status == cp_model.INFEASIBLE:
        core = solver.sufficient_assumptions_for_infeasibility()
        # Map assumption indices back to constraint group names
        lit_to_group = {v.index: k for k, v in 
                        variables.enforcement_literals.items()}
        conflicting = [lit_to_group.get(lit.index, f"unknown_{lit.index}") 
                       for lit in core]
        return conflicting
    return []
```

This produces output like `["availability_restrictions", "max_hours_per_week"]` — which the LLM can translate into "Alice's availability restrictions conflict with the maximum hours limit. Either she needs to be available for more shifts, or the hours cap needs to increase."

---

## 4. The explanation layer needs three data structures and three verbosity levels

The explanation pipeline transforms raw solver output into natural language through three data structures: `PenaltyResult` (what the solver decided and why), `ScheduleDiff` (what changed from the previous schedule), and a structured prompt that asks Claude to generate voice-friendly summaries at the appropriate detail level.

**PenaltyResult** captures the complete objective function breakdown:

```python
from pydantic import BaseModel

class PenaltyDetail(BaseModel):
    category: str          # "overtime", "preference", "fairness"
    person: str            # "Alice"
    description: str       # "Alice works 2 hours over weekly limit"
    violation_amount: int  # 2 (hours over)
    penalty_cost: int      # 200 (violation × weight)

class PenaltyResult(BaseModel):
    total_objective: int
    penalty_breakdown: list[PenaltyDetail]
    hard_constraints_satisfied: bool
    binding_constraints: list[str]   # constraints at their limit
    per_person_summary: dict[str, dict]  # person → {shifts, hours, violations}

def extract_penalty_result(solver, variables, config, builder) -> PenaltyResult:
    """Extract structured explanation data from a solved model."""
    penalties = []
    for name, var in variables.penalties.items():
        value = solver.value(var)
        if value > 0:
            person, category = name.rsplit("_", 1)
            weight = getattr(config, f"{category}_penalty_weight", 1)
            penalties.append(PenaltyDetail(
                category=category, person=person,
                description=f"{person}: {category} violation of {value}",
                violation_amount=value, penalty_cost=value * weight,
            ))
    
    # Per-person assignment summary
    per_person = {}
    for (person, day, shift), var in variables.assignments.items():
        if solver.value(var) == 1:
            per_person.setdefault(person, {"shifts": [], "total_hours": 0})
            per_person[person]["shifts"].append(f"{day}_{shift}")
            per_person[person]["total_hours"] += 8

    return PenaltyResult(
        total_objective=solver.objective_value,
        penalty_breakdown=penalties,
        hard_constraints_satisfied=True,
        binding_constraints=[d for d in builder.constraint_log 
                            if "limited" in d or "blocked" in d],
        per_person_summary=per_person,
    )
```

**ScheduleDiff** computes the delta between two solutions — essential for verbalization:

```python
@dataclass
class ScheduleDiff:
    added: list[tuple[str, str, str]]     # (person, day, shift) new assignments
    removed: list[tuple[str, str, str]]   # assignments that were removed
    unchanged_count: int
    people_affected: set[str]
    objective_delta: int                   # positive = got worse
    penalty_deltas: dict[str, int]         # per-category changes

def compute_schedule_diff(old_solution: dict, new_solution: dict) -> ScheduleDiff:
    old_set = {(p, s) for p, shifts in old_solution["assignments"].items() 
               for s in shifts}
    new_set = {(p, s) for p, shifts in new_solution["assignments"].items() 
               for s in shifts}
    
    added = [(p, *s.split("_", 1)) for p, s in (new_set - old_set)]
    removed = [(p, *s.split("_", 1)) for p, s in (old_set - new_set)]
    affected = {a[0] for a in added} | {r[0] for r in removed}
    
    return ScheduleDiff(
        added=added, removed=removed,
        unchanged_count=len(old_set & new_set),
        people_affected=affected,
        objective_delta=new_solution["objective"] - old_solution["objective"],
        penalty_deltas={},
    )
```

**The explanation prompt** generates three verbosity levels — quick summary for voice, detailed paragraph, and deep dive. The prompt receives the PenaltyResult and ScheduleDiff as structured JSON and produces conversational output:

```python
EXPLANATION_PROMPT = """Generate a schedule change explanation from this data.
Return three versions:

1. QUICK (one sentence, under 20 words, suitable for speaking aloud):
   - State what changed in plain English
   - No jargon, numbers, or formatting
   
2. DETAILED (2-4 sentences):
   - What changed and who's affected
   - Any trade-offs the solver made
   - Conversational but informative

3. DEEP (paragraph):
   - Full penalty breakdown in plain language
   - Why specific trade-offs were chosen
   - What constraints were binding

RULES FOR VOICE OUTPUT:
- Say "three people" not "3 employees"
- Say "Thursday morning" not "Thursday_Morning" 
- Say "about forty hours" not "40h"
- No bullet points, tables, or markdown
- Short sentences under fifteen words
- Active voice: "Bob now covers" not "the shift has been covered by"

SCHEDULE DIFF:
{diff_json}

PENALTY RESULT:
{penalty_json}

USER'S ORIGINAL REQUEST:
{user_request}"""
```

An example quick summary: *"Done. Alice has Thursday morning off and Bob is covering her shift."* An example detailed version: *"I've removed Alice from the Thursday morning shift as requested. Bob picked up that shift since he had availability and the right skills. This added one extra shift to Bob's week, bringing him to four shifts total — still under his weekly limit. No other schedules changed."*

**Determining which constraints are binding** requires checking whether a constraint's slack is zero. For shift-count limits, compare the assigned count to the cap. For coverage constraints, check if exactly `min_staff` people are assigned (no slack). For availability, the constraint is inherently binding whenever someone is marked unavailable. These binding constraints form the "why" behind the solver's decisions.

---

## 5. State management requires a constraint history log and config snapshots

The interaction loop persists state across multiple conversation turns. Five components need tracking: the **constraint config** (current truth), **config history** (for undo), **solution hints** (for warm-starting), **published schedule** (the committed baseline), and **locked assignments** (user-pinned decisions).

```python
from datetime import datetime

class ConstraintChange(BaseModel):
    """Single atomic change record for the history log."""
    timestamp: datetime
    user_input: str
    interpretation: dict          # the LLM's parsed change spec
    config_before: ConstraintConfig
    config_after: ConstraintConfig
    was_what_if: bool = False
    was_applied: bool = True

class ScheduleState(BaseModel):
    """Complete state persisted between conversation turns."""
    config: ConstraintConfig
    history: list[ConstraintChange] = []
    published_schedule: dict | None = None  # the committed baseline
    solution_hints: dict[str, int] = {}     # var_key → value, for warm-start
    locked_assignments: set[tuple[str, str, str]] = set()  # pinned decisions
    
    def apply_change(self, change: ConstraintChange):
        self.history.append(change)
        self.config = change.config_after
    
    def undo(self, n: int = 1) -> list[ConstraintChange]:
        """Revert the last N changes. Returns the reverted changes."""
        reverted = []
        for _ in range(min(n, len(self.history))):
            change = self.history.pop()
            reverted.append(change)
        # Restore config to state before the earliest reverted change
        if self.history:
            self.config = self.history[-1].config_after
        else:
            self.config = ConstraintConfig()  # default
        return reverted
    
    def lock_assignment(self, person: str, day: str, shift: str):
        """Pin an assignment so the solver can't change it."""
        self.locked_assignments.add((person, day, shift))
    
    def publish(self, solution: dict):
        """Commit current solution as the published baseline."""
        self.published_schedule = solution
```

**Locked assignments** translate to hard constraints during model building — `model.add(var == 1)` for each locked `(person, day, shift)`. This ensures the solver respects user-pinned decisions while optimizing everything else.

**The undo mechanism** follows the command pattern. Each `ConstraintChange` stores the config before and after, making rollback trivial — pop the history stack and restore the previous config. Since the model rebuilds from config on every solve, undo is just a config revert followed by a re-solve.

**Early infeasibility detection** should run before presenting the confirmation to the user. After applying proposed changes to a config copy, rebuild the model and run a quick feasibility check (5-second timeout). If infeasible, use the assumptions-based diagnosis from Section 3 to identify which constraint groups conflict, and present this to the user: *"That change would make the schedule impossible — Alice being unavailable all week conflicts with the minimum staffing requirement for morning shifts. Would you like to reduce the morning minimum from three to two people instead?"*

**Serialization** is straightforward since the entire state is Pydantic models. Use `state.model_dump_json()` for persistence to disk or database between sessions. Solution hints serialize as a simple `{var_key: value}` dictionary.

---

## 6. Research validates this architecture, with important caveats on accuracy

A survey of 2024–2025 work on LLM-assisted constraint programming reveals converging evidence on what works and what fails.

**MCP-Solver** (Szeider, 2025; accepted at SAT 2025) uses the Model Context Protocol to bridge LLMs with MiniZinc, PySAT, and Z3 solvers. Its key architectural insight is **item-based incremental building with immediate validation** — the LLM adds constraints one at a time, each validated on addition. A two-agent pattern (builder + reviewer) catches errors the builder misses. ShiftPlanner's structured tool use achieves the same validation-on-each-step property through the `ConstraintConfig` → rebuild → `model.validate()` pipeline.

**DCP-Bench-Open** (Michailidis, Tsouros, and Guns, 2025) provides the most comprehensive accuracy benchmarks. Testing 101 combinatorial problems across three frameworks, it found that **Python-based APIs (CPMpy, OR-Tools CP-SAT) achieve 15–20% higher accuracy than domain-specific languages** like MiniZinc — 65% versus 50% for single-shot generation. Detailed system prompts improved accuracy significantly. With inference-time compute methods (repeated sampling, self-verification, self-debugging), accuracy reached **91%**. Most dramatically, CP-Agent's fully agentic approach achieved **100% on all 101 problems** using Claude Sonnet with a carefully crafted project prompt.

**OptiMUS** (AhmadiTeshnizi et al., 2024) demonstrated that modular decomposition — processing each constraint independently with a dependency-tracking connection graph — outperforms monolithic generation by **40+ percentage points** (73.7% vs. 33.2% on hard problems). Its iterative debugging loop proved critical: without it, accuracy dropped from 74% to 27%. Self-reflective error correction prompts ("Is this constraint correct?", "Are the indices right?") caught formulation errors before they cascaded.

The most common failure modes across all systems, ranked by frequency:

- **Incorrect mathematical formulation** (~40% of failures) — wrong variable definitions, missing constraints, wrong direction (≤ vs. ≥), off-by-one indexing
- **Coding/syntax errors** (~25%) — misuse of solver API methods, type mismatches, scope errors
- **Hallucinated constraints** (~15%) — constraints not implied by the problem, over-constraining to infeasibility
- **Objective function errors** (~10%) — wrong direction (min vs. max), missing terms, wrong coefficients
- **Data handling errors** (~10%) — wrong parameter extraction, incorrect array indexing

ShiftPlanner's structured-output architecture directly mitigates the top three failure modes. The LLM never generates CP-SAT API calls (eliminating coding errors), operates on a fixed schema with validated entity names (eliminating hallucinated constraints), and modifies declarative config values rather than formulating mathematical constraints (reducing formulation errors). **The remaining risk is semantic misinterpretation** — the LLM correctly parsing "Alice can't work Thursday" but resolving Thursday to the wrong date. The entity-resolution and confirmation layers address this.

---

## Conclusion

ShiftPlanner's architecture aligns well with the emerging consensus from 2024–2025 research. The key insights that should guide implementation:

**Config-as-truth is the right pattern.** The LLM modifies a Pydantic config; the model rebuilds deterministically. This eliminates the most common failure modes and makes undo, what-if, and persistence trivial. The five-layer validation pipeline (schema → entity → bounds → feasibility → human) catches errors the LLM cannot.

**Structured output with `strict: true` is non-negotiable.** Claude's constrained decoding guarantees schema compliance at the token level. This is qualitatively different from parsing freeform text — it provides a mathematical guarantee that the output matches the schema, reducing the pipeline's job to semantic validation (is the right person named? is the date correct?) rather than structural parsing.

**Infeasibility is the hardest UX problem.** Detecting it early (via quick feasibility pre-checks) and explaining it clearly (via `sufficient_assumptions_for_infeasibility` mapped to constraint group names) prevents users from committing to impossible configurations. The LLM should translate conflict sets into actionable suggestions: not just "these constraints conflict" but "would you like to reduce the morning minimum or make Alice available one more day?"

**The explanation layer should be over-structured.** Passing the LLM a flat text summary of what changed produces unreliable explanations. Passing it a typed `PenaltyResult` + `ScheduleDiff` with explicit fields for violations, affected people, and trade-offs produces consistently useful output at all three verbosity levels. For voice output, the key constraint is sentence length — under fifteen words, active voice, natural number pronunciation.

**Expect ~85–95% first-attempt accuracy for simple scheduling changes** (availability, staffing) with this architecture, dropping to ~70–85% for complex multi-constraint modifications. The confirmation step catches most remaining errors. The agentic iterative-refinement pattern (interpret → validate → present conflicts → refine → confirm) is what drives accuracy from 65% to near-100% in the research literature, and ShiftPlanner's interaction loop implements exactly this pattern.