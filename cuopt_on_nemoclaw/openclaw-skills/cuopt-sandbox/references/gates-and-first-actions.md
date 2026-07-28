# Gates and first actions (NemoClaw sandbox)

**This sandbox exists to solve with cuOpt.** For schedule, assign, route,
minimize, or allocate-under-constraints tasks, cuOpt is turn one — not
turn two after the user corrects you.

## Before smoke passes (Gate 3)

| Ready now | Wait until cuOpt smoke succeeds |
|---|---|
| `probe_cuopt.py` | Timed assignment output (schedule, roster, shift plan) |
| Run capability-aware gRPC smoke scripts | Greedy / heuristic / backtracking code |
| Inspect uploaded CSVs for **columns and constraints** | "Draft plan while cuOpt sets up" |
| Ask **one** blocking clarification | `ortools`, `pulp`, hand-rolled search |
| Write `/sandbox/<job>.py` for any nontrivial cuOpt model | Feasibility verdict without cuOpt status |

Inspecting uploaded data for structure is fine; emit a completed assignment
plan only after cuOpt returns a solver status.

Existing `/sandbox` scripts and result files are historical artifacts, not
evidence that the current request was solved. They may be inspected as drafts,
but rerun the gates and solve the current inputs through the selected cuOpt
gRPC path.

## Mandatory order (every optimization task)

1. **Probe** — `bash -lc 'python3 /sandbox/probe_cuopt.py'`
2. **Select execution** — if `python_async_grpc: available`, use the
   cancelable `Client`; otherwise use the legacy remote fallback. See
   `references/grpc-connectivity-and-smoke.md`.
3. **Smoke** — run `/sandbox/smoke_lp.py` (+ `smoke_milp.py` for discrete
   scheduling MILP). Confirm its `execution_mode` and successful status.
4. **Formulation skills** — read vendored `*-formulation` + `cuopt-*-api-*`
5. **Build and solve** — real model via cuOpt; report job ID, job status,
   solver termination, and objective

Start cuOpt gates on the first optimization turn — the user does not need
to say "use cuOpt" first.

## Scheduling and assignment over time

Uploaded tables + language like **"build me a schedule"**, "assign shifts",
"fill time slots", or "minimize conflicts/cost under capacity" → **MILP
via cuOpt gRPC**, not a custom Python scheduler.

The user **does not** need to say minimize, optimal, or best. Feasibility
under capacity, unavailability, and no-double-booking rules is expressed
as **hard constraints** in a MILP; cuOpt satisfies them (and can optimize
a secondary objective when you define one).

Examples: shift/roster planning, timetabling, resource–slot assignment,
league or event scheduling (e.g. games to courts and slots).

After gates: `numerical-optimization-formulation` +
`cuopt-numerical-optimization-api-python` → cuOpt `Problem` with INTEGER
vars → report status, objective, and assignments.

## "Feasibility only" / "fastest path" (wrong in this sandbox)

Agents sometimes skip cuOpt with reasoning like *"no explicit objective"*
or *"greedy is enough for a valid schedule."* That violates this skill.

| Wrong rationalization | Correct action |
|---|---|
| "User didn't ask to minimize" | Constructive + constraint data → cuOpt anyway |
| "cuOpt is for optimization, not feasibility" | Feasibility = constraints; cuOpt is the solver here |
| "Greedy is faster for a first result" | Run probe → smoke → cuOpt; no greedy first deliverable |
| "I'll optimize later if they want" | First schedule output must come from cuOpt after gates |
| "Data looks simple" | Simple data still gets cuOpt MILP in this sandbox |

If the secondary objective is unclear, ask one focused question or state
a default (e.g. minimize penalty slacks, balance slot usage) — then solve
with cuOpt.

## Common mistakes (and the fix)

| Mistake | Fix |
|---|---|
| Heuristic assignment plan first, cuOpt after user correction | Run gates 1–3 before any assigner code |
| `from cuopt import milp` then pivot to heuristics | Use `references/python-imports.md`; import errors mean fix the path |
| Greedy solver to "explore structure" | Use formulation skills; cuOpt is the feasibility engine |
| "No minimize in prompt → feasibility greedy OK" | Constructive + CSVs → cuOpt; see intent-and-triggers.md |
| "Valid schedule first, cuOpt later" | First assignment output must be cuOpt after gates |
| Orchestration steps treated as permission to skip gates | Ingestion is interpretation only — gates still apply |
