# Architecting a background CP-SAT solver for FastAPI

**CP-SAT releases the Python GIL during solving, which fundamentally simplifies the architecture.** Because the solver's C++ core runs outside the GIL, you can run solves in a simple thread rather than a separate process — eliminating serialization overhead, enabling direct cancellation via `StopSearch()`, and letting solution callbacks bridge naturally into the asyncio event loop. The recommended architecture for a self-hosted, single-server ShiftPlanner is a `ThreadPoolExecutor` running the solver, a generation counter to discard stale results, an `asyncio.Queue` piping callback events to an SSE stream, and a full model rebuild from the database on each solve with solution hints for warm-starting.

This report covers each of the six areas in depth, with production-ready Python code examples and an integrated architecture at the end.

---

## 1. Threading beats multiprocessing because CP-SAT releases the GIL

The single most important fact for this architecture is that **OR-Tools CP-SAT releases the GIL** when `solver.Solve()` enters the C++ core. Evidence: the officially recommended `threading.Timer`-based `StopSearch()` pattern — which would deadlock if the GIL were held — is demonstrated by the OR-Tools maintainer Laurent Perron in multiple GitHub discussions. The solver acquires a `threading.Lock` internally (not the GIL), and its C++ thread pool runs `num_workers` search threads entirely outside Python.

This means `ThreadPoolExecutor` is the correct executor for a FastAPI integration. Here is a comparison of realistic options:

| Approach | GIL handling | Cancellation | Progress | Ops complexity | Verdict |
|---|---|---|---|---|---|
| `ThreadPoolExecutor` | GIL released by CP-SAT; threads run concurrently | Direct `StopSearch()` call from any thread | Callbacks share memory; zero-copy | **Zero** external deps | **Recommended** |
| `ProcessPoolExecutor` | Separate process bypasses GIL entirely | Requires `multiprocessing.Event` + cooperative checking | Requires `Pipe` or `Queue` for IPC | Low, but pickle overhead | Viable but unnecessary |
| Celery (prefork) | Separate worker process | `revoke(terminate=True)` sends SIGTERM — blunt | Requires Redis pub/sub for progress | **High** — Redis, worker process, monitoring | Overkill for single-server |
| Ray | Separate worker processes | `ray.cancel()` — better than Celery | Object store for IPC | Medium — heavyweight runtime (~150 MB deps) | Overkill for single-server |
| `BackgroundTasks` | Same event loop; **blocks all requests** if async | None | None | Lowest | **Not suitable** for CPU-bound work |

The threading approach works because during the seconds-to-minutes that `solver.Solve()` runs, the event loop thread is free to handle HTTP requests, WebSocket frames, and SSE pushes. The GIL is only briefly re-acquired when Python callbacks (`on_solution_callback`, `log_callback`) execute — these are microsecond operations that cause negligible contention.

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Single-worker pool: one solve at a time, dedicated thread
solver_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="solver")

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    solver_pool.shutdown(wait=True, cancel_futures=True)

app = FastAPI(lifespan=lifespan)

async def run_solve_in_thread(solve_fn, *args):
    """Run a blocking solve function without blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(solver_pool, solve_fn, *args)
```

Set `max_workers=1` because CP-SAT itself is internally parallel (`num_workers` defaults to all cores). Running two concurrent solves would cause CPU oversubscription. The single-worker pool serializes solves while the cancellation layer (Section 2) ensures only the latest request actually runs.

For the `num_workers` parameter on the solver: on a machine with *N* cores, set `solver.parameters.num_workers` to *N* − 1 or *N* − 2, leaving headroom for the event loop thread and OS overhead. For a ~40-person scheduling problem, **8 workers** is a good default that activates CP-SAT's full portfolio of subsolvers (LNS, feasibility pump, linear relaxation, and more).

---

## 2. Cancellation via `StopSearch()` with a shared callback reference

CP-SAT provides two cancellation mechanisms. The first is `CpSolverSolutionCallback.StopSearch()`, callable from any thread. The second, available since OR-Tools v9.10, is `solver.stop_search()` (a method directly on the solver instance). Both set an internal flag that the C++ engine checks periodically — response latency is typically **milliseconds**.

The key design: maintain a reference to the active callback object, and call `StopSearch()` on it from the asyncio thread when a new solve request arrives.

```python
from ortools.sat.python import cp_model
import asyncio, time

class CancellableSolveCallback(cp_model.CpSolverSolutionCallback):
    """Solution callback that supports external cancellation and progress reporting."""

    def __init__(self, progress_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self._progress_queue = progress_queue
        self._loop = loop
        self._cancelled = False

    def on_solution_callback(self):
        # Push progress into the async queue (thread-safe via call_soon_threadsafe)
        event = {
            "type": "solution",
            "objective": self.objective_value,
            "bound": self.best_objective_bound,
            "gap": self._relative_gap(),
            "wall_time": self.wall_time,
            "solutions_found": self.num_booleans,  # or a custom counter
        }
        self._loop.call_soon_threadsafe(self._progress_queue.put_nowait, event)

    def cancel(self):
        """Called from any thread to stop the solve."""
        self._cancelled = True
        self.StopSearch()

    def _relative_gap(self) -> float:
        if abs(self.objective_value) < 1e-9:
            return 0.0
        return abs(self.objective_value - self.best_objective_bound) / max(
            1.0, abs(self.objective_value)
        )
```

**What happens to partially-solved state after `StopSearch()`:** the solver returns status `FEASIBLE` if it had found at least one solution before cancellation, or `UNKNOWN` if no feasible solution was found yet. In either case, `solver.objective_value` and variable values are accessible for the last feasible solution found. This is critical — **a cancelled solve with a `FEASIBLE` result is a perfectly usable schedule**, just not provably optimal. Your system should treat it as a valid fallback.

```python
def execute_solve(model, callback, time_limit=60.0):
    """Blocking function that runs in the solver thread."""
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 8
    solver.parameters.log_search_progress = True
    status = solver.solve(model, callback)
    return status, solver
```

The time limit acts as a hard safety net — even if cancellation logic fails, the solve will terminate. Always set it.

---

## 3. A generation counter ensures the system always solves the latest state

When a user makes several rapid natural language changes, the system must guarantee: (a) only the latest model state gets solved, (b) stale results are discarded, and (c) in-flight solves are cancelled promptly. The right pattern combines **debouncing**, **generation counting**, and **latest-wins cancellation** into a single coordinator class.

```python
import asyncio, itertools, logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("shiftplanner.solver")

@dataclass
class SolveResult:
    generation: int
    status: int  # cp_model status code
    solution: Optional[dict]
    objective: Optional[float]
    wall_time: float
    was_cancelled: bool = False

class SolverCoordinator:
    """Manages solve lifecycle: debouncing, cancellation, generation tracking."""

    def __init__(
        self,
        build_and_solve_fn,       # Callable that builds model and solves
        on_result_fn,             # Callback when a valid result arrives
        debounce_seconds: float = 0.3,
    ):
        self._build_and_solve = build_and_solve_fn
        self._on_result = on_result_fn
        self._debounce_seconds = debounce_seconds
        self._generation = 0
        self._gen_counter = itertools.count(1)
        self._active_callback: Optional[CancellableSolveCallback] = None
        self._pending_task: Optional[asyncio.Task] = None
        self._progress_queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()  # Protects state mutations

    async def submit_change(self, schedule_input: dict):
        """Called when user submits a change. Debounces and triggers solve."""
        async with self._lock:
            # Bump generation
            self._generation = next(self._gen_counter)
            gen = self._generation

            # Cancel any pending debounce timer
            if self._pending_task and not self._pending_task.done():
                self._pending_task.cancel()

            # Cancel any in-flight solve
            if self._active_callback is not None:
                self._active_callback.cancel()
                logger.info(f"Cancelled solve gen={gen - 1}")

        # Start debounced solve
        self._pending_task = asyncio.create_task(
            self._debounced_solve(gen, schedule_input)
        )

    async def _debounced_solve(self, generation: int, schedule_input: dict):
        """Wait for the debounce window, then solve if still current."""
        await asyncio.sleep(self._debounce_seconds)

        async with self._lock:
            if generation != self._generation:
                return  # A newer request arrived during debounce; abort

        # Clear progress queue
        while not self._progress_queue.empty():
            self._progress_queue.get_nowait()

        loop = asyncio.get_running_loop()
        callback = CancellableSolveCallback(self._progress_queue, loop)

        async with self._lock:
            self._active_callback = callback

        # Run solve in thread pool
        try:
            status, solver = await asyncio.get_running_loop().run_in_executor(
                solver_pool,
                self._build_and_solve,
                schedule_input,
                callback,
            )
        except Exception as e:
            logger.error(f"Solve gen={generation} failed: {e}")
            await self._on_result(SolveResult(
                generation=generation, status=-1, solution=None,
                objective=None, wall_time=0, was_cancelled=False,
            ))
            return
        finally:
            async with self._lock:
                if self._active_callback is callback:
                    self._active_callback = None

        # Check if result is still current
        async with self._lock:
            is_current = (generation == self._generation)

        if not is_current:
            logger.info(f"Discarding stale result gen={generation}")
            return

        result = SolveResult(
            generation=generation,
            status=status,
            solution=extract_solution(solver) if status in (
                cp_model.OPTIMAL, cp_model.FEASIBLE
            ) else None,
            objective=solver.objective_value if status in (
                cp_model.OPTIMAL, cp_model.FEASIBLE
            ) else None,
            wall_time=solver.wall_time,
            was_cancelled=callback._cancelled,
        )
        await self._on_result(result)
```

**Why debouncing matters here:** without a **300 ms** debounce window, a user typing a natural-language constraint change that triggers re-parsing every keystroke could launch dozens of solves. The debounce ensures only the final state in a burst of changes triggers a solve. If the user makes a change while a solve is already running, the in-flight solve is cancelled immediately via `StopSearch()`, the debounce timer starts, and the new solve launches after the quiet period.

**Why generation counting is essential even with cancellation:** `StopSearch()` is not instantaneous — the solver may take a few hundred milliseconds to wind down. During that window, a second cancellation or a new solve request could arrive. The generation counter provides a definitive, race-free way to determine whether a completed result is still relevant. Only results matching `self._generation` are applied.

---

## 4. Solution callbacks pipe into SSE through an asyncio queue

The `CancellableSolveCallback` above already pushes progress events into an `asyncio.Queue` via `call_soon_threadsafe`. The SSE endpoint drains this queue and yields events to the client. Install `sse-starlette` (`pip install sse-starlette`) for standards-compliant Server-Sent Events.

```python
from sse_starlette.sse import EventSourceResponse
from fastapi import Request
import json

@app.get("/solve/stream")
async def solve_stream(request: Request):
    """SSE endpoint that streams solver progress to the frontend."""
    coordinator = app.state.solver_coordinator  # Initialized at startup

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(
                    coordinator._progress_queue.get(), timeout=2.0
                )
                yield {
                    "event": event["type"],
                    "data": json.dumps(event),
                }
                if event["type"] in ("complete", "error", "cancelled"):
                    break
            except asyncio.TimeoutError:
                # Send keepalive to prevent proxy/browser timeout
                yield {"event": "ping", "data": ""}

    return EventSourceResponse(event_generator())
```

**What to surface during a live solve** — four pieces of information are genuinely useful to users and available from the callback:

- **Current best objective value** (`self.objective_value`): translates to a human-readable quality metric like "97% of shift preferences satisfied."
- **Optimality gap** (`abs(objective - bound) / abs(objective)`): tells the user how close to theoretically perfect the current schedule is. A gap of 2% means "at most 2% improvement is possible."
- **Elapsed wall time** (`self.wall_time`): simple progress indicator.
- **Number of solutions found**: reassures the user the solver is making progress.

The client-side integration is straightforward:

```javascript
const source = new EventSource("/solve/stream");
source.addEventListener("solution", (e) => {
    const data = JSON.parse(e.data);
    updateProgress({
        quality: `${(100 * data.objective / maxObjective).toFixed(1)}%`,
        gap: `${(data.gap * 100).toFixed(1)}% from optimal`,
        elapsed: `${data.wall_time.toFixed(1)}s`,
    });
});
source.addEventListener("complete", (e) => {
    const data = JSON.parse(e.data);
    displaySchedule(data.solution);
    source.close();
});
```

For bidirectional communication (e.g., the user clicking "Cancel" or "Accept current solution"), a **WebSocket** is more appropriate. You can run both: SSE for progress push, plus a REST endpoint or WebSocket for user commands. For ShiftPlanner's interactive loop, a WebSocket that handles both solve requests and progress streaming is the cleanest single-connection approach:

```python
@app.websocket("/ws/solve")
async def solve_ws(websocket: WebSocket):
    await websocket.accept()
    coordinator = app.state.solver_coordinator
    try:
        while True:
            # Listen for commands and progress concurrently
            msg_task = asyncio.create_task(websocket.receive_json())
            progress_task = asyncio.create_task(
                coordinator._progress_queue.get()
            )
            done, pending = await asyncio.wait(
                {msg_task, progress_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for t in pending:
                t.cancel()

            for task in done:
                result = task.result()
                if task is msg_task:
                    # User sent a command
                    if result.get("action") == "submit_change":
                        await coordinator.submit_change(result["data"])
                    elif result.get("action") == "cancel":
                        if coordinator._active_callback:
                            coordinator._active_callback.cancel()
                elif task is progress_task:
                    await websocket.send_json(result)
    except WebSocketDisconnect:
        pass
```

---

## 5. Rebuild the model from the database on every solve, with solution hints

CP-SAT models are **not designed for incremental modification**. You cannot remove constraints — only add new ones. The `only_enforce_if()` mechanism with enforcement literals can toggle constraints, but accumulating dead constraints across dozens of solve cycles degrades model clarity and risks subtle bugs. **Rebuilding the model from a persistent data layer on each solve is the standard, recommended pattern.**

This is not a performance concern. For a 40-person scheduling problem, model construction takes **single-digit milliseconds** — the time is dominated entirely by solving. The CP-SAT Primer by Dominik Krupke (the most authoritative third-party guide) explicitly recommends this approach.

**What to persist vs. what to reconstruct:**

| Persist (database) | Reconstruct (in-memory) |
|---|---|
| Employee records, skills, availability | `CpModel` object and all variables |
| Shift definitions, coverage requirements | `CpSolver` instance |
| User-defined constraints and preferences | Constraint expressions |
| Last valid solution (assignments + objective) | Callback objects |
| Solver configuration (time limit, gap limit) | — |

The **model-building function** should be a pure function: database state in, `CpModel` out. This makes it testable, reproducible, and safe to call from any thread.

```python
from ortools.sat.python import cp_model
from typing import Optional

def build_schedule_model(
    employees: list[dict],
    shifts: list[dict],
    constraints: list[dict],
    previous_solution: Optional[dict] = None,
) -> cp_model.CpModel:
    model = cp_model.CpModel()

    # --- Variables ---
    # shifts_vars[(emp_id, day, shift_type)] = BoolVar
    shifts_vars = {}
    for emp in employees:
        for day in range(7):
            for shift in shifts:
                var = model.new_bool_var(
                    f"shift_e{emp['id']}_d{day}_s{shift['id']}"
                )
                shifts_vars[(emp["id"], day, shift["id"])] = var

    # --- Hard constraints ---
    # One shift per employee per day
    for emp in employees:
        for day in range(7):
            model.add_at_most_one(
                shifts_vars[(emp["id"], day, s["id"])] for s in shifts
            )

    # Coverage: each shift-day needs minimum staff
    for day in range(7):
        for shift in shifts:
            model.add(
                sum(shifts_vars[(e["id"], day, shift["id"])]
                    for e in employees)
                >= shift["min_staff"]
            )

    # User-defined constraints (from natural language → parsed rules)
    for c in constraints:
        _add_parsed_constraint(model, shifts_vars, c, employees, shifts)

    # --- Objective: maximize preference satisfaction ---
    preference_terms = []
    for emp in employees:
        for day in range(7):
            for shift in shifts:
                weight = emp.get("preferences", {}).get(
                    (day, shift["id"]), 0
                )
                if weight:
                    preference_terms.append(
                        weight * shifts_vars[(emp["id"], day, shift["id"])]
                    )
    if preference_terms:
        model.maximize(sum(preference_terms))

    # --- Solution hints from previous solve ---
    if previous_solution:
        for (emp_id, day, shift_id), var in shifts_vars.items():
            hint_val = previous_solution.get((emp_id, day, shift_id), 0)
            model.add_hint(var, hint_val)

    return model, shifts_vars
```

**Solution hints are the key to fast re-solves.** `model.add_hint(var, value)` tells the solver to try branching toward that value first. When a user changes one constraint and the previous solution is still mostly valid, hints let the solver find the first feasible solution in **milliseconds** rather than seconds — then spend remaining time improving it. Hints do not need to satisfy all constraints; the solver treats them as suggestions, not requirements.

**State synchronization pattern:**

```python
class ScheduleStateManager:
    def __init__(self, db):
        self.db = db
        self._last_valid_solution: Optional[dict] = None
        self._last_valid_objective: Optional[float] = None

    async def on_solve_result(self, result: SolveResult):
        if result.solution is not None:
            # Persist the new valid solution
            self._last_valid_solution = result.solution
            self._last_valid_objective = result.objective
            await self.db.save_solution(result.solution, result.objective)
        elif result.status == cp_model.INFEASIBLE:
            # Don't overwrite — keep last valid solution
            pass  # Frontend shows error + previous schedule

    def get_hints(self) -> Optional[dict]:
        return self._last_valid_solution

    async def build_current_model(self) -> tuple:
        data = await self.db.load_schedule_input()
        return build_schedule_model(
            employees=data["employees"],
            shifts=data["shifts"],
            constraints=data["constraints"],
            previous_solution=self._last_valid_solution,
        )
```

---

## 6. Robust error handling requires status-aware fallback logic

CP-SAT returns five possible statuses. Each demands a different user-facing response and system behavior:

**`OPTIMAL`** — the schedule is provably the best possible. Display it with confidence. This is common for well-constrained 40-person problems.

**`FEASIBLE`** — a valid schedule exists but optimality was not proven (time limit or `StopSearch()`). Display it — **feasible solutions from CP-SAT are typically within a few percent of optimal**. Show the optimality gap so users know the quality.

**`INFEASIBLE`** — no valid schedule exists given the current constraints. This is the most important error to handle well. When a user's natural language change creates a contradiction (e.g., "Alice must work Monday" + "Alice cannot work any day this week"), the system needs to explain *which constraints conflict*.

**`UNKNOWN`** — the solver hit a time limit before finding any solution or proving infeasibility. Rare for 40-person problems but possible with pathological constraint combinations or very short time limits.

**`MODEL_INVALID`** — a programming error in model construction (e.g., enforcement literals on `add_exactly_one`, which is unsupported). Should never reach production; catch during testing.

```python
async def handle_solve_result(result: SolveResult, state: ScheduleStateManager):
    match result.status:
        case cp_model.OPTIMAL:
            await state.on_solve_result(result)
            return {"status": "optimal", "schedule": result.solution,
                    "objective": result.objective}

        case cp_model.FEASIBLE:
            await state.on_solve_result(result)
            gap_pct = f"{result.gap * 100:.1f}%" if hasattr(result, 'gap') else "unknown"
            return {"status": "feasible", "schedule": result.solution,
                    "objective": result.objective,
                    "message": f"Good schedule found ({gap_pct} from optimal)"}

        case cp_model.INFEASIBLE:
            # Fall back to last valid solution
            last = state._last_valid_solution
            conflicts = await diagnose_infeasibility(state)
            return {"status": "infeasible", "schedule": last,
                    "message": "No valid schedule exists with current constraints",
                    "conflicting_constraints": conflicts}

        case cp_model.UNKNOWN:
            last = state._last_valid_solution
            return {"status": "timeout", "schedule": last,
                    "message": "Solver timed out. Showing previous schedule."}

        case cp_model.MODEL_INVALID:
            logger.error(f"MODEL_INVALID — this is a bug: gen={result.generation}")
            return {"status": "error",
                    "message": "Internal error in schedule model"}
```

**Diagnosing infeasibility with assumptions** is CP-SAT's analog of an Irreducible Infeasible Subsystem (IIS). Wrap each user-defined constraint with an enforcement literal, add those literals as assumptions, and if the solve returns `INFEASIBLE`, call `solver.sufficient_assumptions_for_infeasibility()` to get the conflicting subset:

```python
async def diagnose_infeasibility(state: ScheduleStateManager) -> list[str]:
    """Rebuild model with assumptions to find conflicting constraints."""
    data = await state.db.load_schedule_input()
    model = cp_model.CpModel()

    # Build core model (coverage, one-shift-per-day) without assumptions
    shifts_vars = _build_core_variables_and_constraints(model, data)

    # Add each user constraint with an assumption literal
    assumption_literals = {}
    for c in data["constraints"]:
        indicator = model.new_bool_var(f"assume_{c['id']}")
        _add_parsed_constraint(
            model, shifts_vars, c, data["employees"], data["shifts"],
            enforce_if=indicator,
        )
        assumption_literals[indicator] = c

    model.add_assumptions(list(assumption_literals.keys()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    solver.parameters.num_workers = 1  # Single-thread for assumption analysis
    status = solver.solve(model)

    if status == cp_model.INFEASIBLE:
        core = solver.sufficient_assumptions_for_infeasibility()
        # Map indices back to constraint descriptions
        conflict_names = []
        for idx in core:
            for lit, constraint in assumption_literals.items():
                if lit.index == idx:
                    conflict_names.append(constraint["description"])
        return conflict_names

    return ["Could not identify specific conflicts"]
```

**A caveat from the OR-Tools documentation:** `sufficient_assumptions_for_infeasibility()` returns a sufficient (but not necessarily minimal) subset. It works best with `num_workers=1`. For most practical scheduling problems, the returned subset is small and actionable.

**Worker process crashes** are a non-issue with the threading approach (a thread crash takes down the whole process, but this is extremely rare with CP-SAT's mature C++ core). For defense-in-depth, wrap the solve call in a try/except that catches all exceptions and returns them as error results.

---

## Integrated architecture ties all six pieces together

Here is the complete wiring, showing how the coordinator, model builder, SSE stream, and error handler connect:

```python
# app.py — complete FastAPI application skeleton
import asyncio, logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse
from ortools.sat.python import cp_model

logger = logging.getLogger("shiftplanner")

solver_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="solver")

def blocking_build_and_solve(schedule_input, callback):
    """Runs in the solver thread. Builds model, solves, returns results."""
    model, shifts_vars = build_schedule_model(
        employees=schedule_input["employees"],
        shifts=schedule_input["shifts"],
        constraints=schedule_input["constraints"],
        previous_solution=schedule_input.get("hints"),
    )
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60
    solver.parameters.num_workers = 8
    solver.parameters.relative_gap_limit = 0.02  # Stop at 2% gap

    status = solver.solve(model, callback)

    # Push final event through the callback's queue
    loop = callback._loop
    final_event = {
        "type": "complete",
        "status": status,
        "objective": (solver.objective_value
                      if status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
                      else None),
        "wall_time": solver.wall_time,
    }
    loop.call_soon_threadsafe(callback._progress_queue.put_nowait, final_event)
    return status, solver

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await init_database()
    state_mgr = ScheduleStateManager(db)
    coordinator = SolverCoordinator(
        build_and_solve_fn=blocking_build_and_solve,
        on_result_fn=lambda r: handle_solve_result(r, state_mgr),
        debounce_seconds=0.3,
    )
    app.state.coordinator = coordinator
    app.state.state_mgr = state_mgr
    yield
    solver_pool.shutdown(wait=True)

app = FastAPI(lifespan=lifespan)

@app.post("/schedule/change")
async def submit_change(change: dict):
    """User submits a constraint change via natural language."""
    parsed = parse_nl_to_constraint(change["text"])
    await app.state.state_mgr.db.save_constraint(parsed)
    schedule_input = await app.state.state_mgr.db.load_schedule_input()
    schedule_input["hints"] = app.state.state_mgr.get_hints()
    await app.state.coordinator.submit_change(schedule_input)
    return {"status": "accepted", "generation": app.state.coordinator._generation}

@app.get("/schedule/stream")
async def schedule_stream(request: Request):
    """SSE stream of solver progress."""
    queue = app.state.coordinator._progress_queue

    async def events():
        while not await request.is_disconnected():
            try:
                event = await asyncio.wait_for(queue.get(), timeout=2.0)
                yield {"event": event["type"], "data": json.dumps(event)}
                if event["type"] in ("complete", "error"):
                    break
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": ""}

    return EventSourceResponse(events())

@app.get("/schedule/current")
async def get_current():
    """Returns the last valid schedule (always available as fallback)."""
    sol = app.state.state_mgr._last_valid_solution
    return {"schedule": sol} if sol else {"schedule": None, "message": "No schedule computed yet"}
```

The data flow is:

1. User POSTs a natural language change → parsed into a constraint → saved to DB.
2. `SolverCoordinator.submit_change()` cancels any in-flight solve via `StopSearch()`, starts a **300 ms debounce timer**.
3. After debounce, the coordinator bumps the generation counter and submits a `blocking_build_and_solve` call to the thread pool.
4. The solver thread rebuilds the model from the full DB state, applies solution hints from the last valid solution, and calls `solver.Solve()`.
5. During solving, `CancellableSolveCallback.on_solution_callback()` pushes progress events into the `asyncio.Queue` via `call_soon_threadsafe`.
6. The SSE endpoint drains the queue and streams events to the frontend.
7. On completion, the coordinator checks the generation counter. If current, the result is applied to the state manager and persisted. If stale, it is discarded.
8. On `INFEASIBLE`, the system retains the last valid schedule and runs a diagnostic solve with assumptions to identify conflicting constraints.

---

## Conclusion

The architecture hinges on one underappreciated fact: **CP-SAT releases the GIL**, making the entire system dramatically simpler than it would be with a purely-Python solver. Threading replaces multiprocessing, eliminating serialization and IPC complexity. `StopSearch()` provides sub-second cancellation without signals or process termination. Solution callbacks share memory with the event loop thread, enabling zero-copy progress streaming.

The three most important design decisions are: **rebuild the model from scratch on every solve** (it costs milliseconds and eliminates accumulated state bugs), **always apply solution hints from the previous result** (they compress re-solve time from seconds to near-instant first-feasible), and **never overwrite the last valid solution until a new valid one is confirmed** (this guarantees the system always has a displayable schedule). The generation counter and debouncer are the glue that makes rapid interactive changes safe — without them, race conditions between overlapping solves would corrupt the schedule state.

For a 40-person scheduling problem on a single server, this architecture handles the typical case (sub-5-second solves) with minimal latency and the worst case (60+ second solves) with graceful cancellation, progress feedback, and reliable fallback to the last known good schedule.