---
name: cuopt-first
description: MANDATORY in NemoClaw sandbox. If you only see tool_search/tool_describe/tool_call, run tool_search (query read or shell) BEFORE claiming you cannot read files or run commands — see always-tool-discovery. STOP before any schedule/heuristic/draft-plan output. FIRST actions: (1) tool_search→exec if needed, (2) probe_cuopt.py, (3) cuopt-remote-env + smoke with CUOPT_REMOTE_HOST/PORT. Do NOT use from cuopt import milp — MILP is cuopt.linear_programming.problem.Problem with INTEGER vars; see cuopt-python-api. Do NOT wait for user to say "use cuOpt". Triggers: schedule, league, CSV upload, minimize, assign, MILP, doubleheader, ImportError, ModuleNotFoundError, wrong import path.
---

# cuOpt First (NemoClaw Sandbox)

**This sandbox exists to solve with cuOpt.** If the user's request is an
optimization problem — schedule, assign, route, minimize, maximize,
allocate under constraints — **cuOpt is turn one, not turn two after the
user corrects you.**

## The rule

| Allowed before cuOpt smoke passes | **Not allowed** before cuOpt smoke passes |
|---|---|
| `probe_cuopt.py` | A schedule, roster, or assignment output |
| Read `cuopt-remote-env`, set `CUOPT_REMOTE_*` | Greedy / heuristic / backtracking solver code |
| LP smoke test (`Using remote GPU backend` + `Optimal`) | "Here's a draft plan while we set up cuOpt" |
| Read CSV/Excel to infer **columns and constraints** | Capacity-only "probably feasible/infeasible" verdict |
| Ask **one** blocking clarification question | `ortools`, `pulp`, hand-rolled MIP search |
| Write `/sandbox/solve.py` **for cuOpt** | Apologizing for using a heuristic — you should not have used one |

**Interpretation ≠ answer.** You may inspect `teams.csv` to learn that
rows are teams and `games.csv` lists matchups. You may **not** emit a
completed season schedule, slot assignments, or "I built a heuristic
schedule with doubleheaders minimized" until cuOpt returns a solver
status on the real model.

## Mandatory first actions (in order)

Do these **before** any optimization answer, **even if** the user
uploaded data and asked a natural-language planning question:

0. **Tools (every session).** If your tool list is only
   `tool_search` / `tool_describe` / `tool_call`, run `tool_search`
   (`query: "read"` to read CSVs, `query: "shell"` for probe/exec).
   **Never ask the user to paste file contents.** See
   `always-tool-discovery`.
1. **`tool_call exec`** → `bash -lc 'python3 /sandbox/probe_cuopt.py'`
2. Read **`cuopt-remote-env`** → export `CUOPT_REMOTE_HOST` /
   `CUOPT_REMOTE_PORT` in the same shell as Python
3. Run **LP smoke test** → `python3 /sandbox/smoke_lp.py` with
   `CUOPT_REMOTE_*` → confirm `Using remote GPU backend` + `status=Optimal`
4. For MILP scheduling: also run `/sandbox/smoke_milp.py` (same env vars)
5. Read **`cuopt-python-api`** — copy import lines for `/sandbox/solve.py`;
   **never** `from cuopt import milp`
6. Read **`cuopt-sandbox`** Four Gates + problem-family routing
7. **Then** formulate and submit the real problem to cuOpt

Steps 1–3 are infrastructure, not "skipping ahead of data inspection."
They take seconds. Run them in parallel with skimming file headers if
needed — but **never** skip them.

## Scheduling / league / CSV tasks

Language like "build the season schedule", "assign games to slots",
"minimize doubleheaders", "balance home/away", uploaded league tables
→ **MILP via cuOpt gRPC**, not a custom Python scheduler.

Default flow:

1. Gates above (probe → env → smoke)
2. **`cuopt-python-api`** — mandatory imports (do not guess `cuopt.milp`)
3. `numerical-optimization-formulation` + `cuopt-numerical-optimization-api-python`
4. cuOpt `Problem` with binary/integer assignment vars + cuOpt solve
5. Report `Problem.Status.name`, objective, assignments

Do **not** write a nested-loop or greedy assigner "to test feasibility"
or "to give the user something quickly."

**One solve at a time:** after you submit to cuOpt, poll until
`time_limit` returns a terminal status (`Optimal`, `FeasibleFound`,
time-limit stop, etc.). Do not start a second job because the first
"is taking too long" — see `cuopt-sandbox` "Long-running solves".

## Anti-pattern — wrong import → heuristic fallback

> `from cuopt import milp` failed. I'll use a greedy scheduler instead.

**Wrong.** MILP uses `from cuopt.linear_programming.problem import Problem,
INTEGER`. Run the verify one-liner in `cuopt-python-api`, then build the
real model. Import errors are not cuOpt outages.

## Anti-pattern — heuristic first, cuOpt after user correction

> You're right — I should have started with cuOpt. That was my miss. I
> used a heuristic first when this should be treated as a MILP scheduling
> problem. I'll model this with cuOpt now.

**This message means you already failed.** The user should never have
had to send the correction. The heuristic output should never have
been produced. Do not pattern-match on apologizing — **prevent** the
heuristic pass entirely by running steps 1–3 before any assigner code.

## Anti-pattern — "explore structure" before cuOpt

> Let me first run a quick feasibility check / greedy pass to understand
> the constraint structure, then I'll move to cuOpt.

Wrong. cuOpt **is** the feasibility and optimization engine here.
Structure exploration belongs in formulation (variables, constraints),
not in a parallel non-cuOpt solver.

## When orchestration skills apply

If `optimization-from-data-orchestrator` or `tabular-optimization-ingestion`
is in play: they govern **interpretation**, not permission to skip cuOpt.
In this sandbox, add **step 0: cuopt-first gates** before any step that
could produce user-visible optimization output.

## Related skills

- `cuopt-python-api` — copy-paste imports; no `cuopt.milp`
- `cuopt-sandbox` — full sandbox wiring (gates, routing, long-running solves)
- `cuopt-remote-env` — env vars and cudaError diagnostics
- `always-tool-discovery` — reaching `read`/`exec` when tools are compact
