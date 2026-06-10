---
name: cuopt-python-api
description: STOP on ImportError, ModuleNotFoundError, or guessed imports (from cuopt import milp, import cuopt.milp, cuopt.solve). LP/MILP/QP share ONE Python entrypoint cuopt.linear_programming.problem.Problem — MILP uses INTEGER variables, not a separate milp module. With CUOPT_REMOTE_HOST/PORT set before Python starts, remote gRPC MILP works in this sandbox. One failed import is NOT proof cuOpt is unavailable — run the verify command below, then read cuopt-numerical-optimization-api-python. Triggers: scheduling MILP, assignment, import failed, wrong API path.
---

# cuOpt Python API — sandbox copy-paste (LP / MILP / QP)

**Do not invent import paths.** There is no `cuopt.milp`, no
`from cuopt import milp`, and no top-level `cuopt.Problem`.

LP, MILP, and QP all use the same class:

```python
from cuopt.linear_programming.problem import Problem, CONTINUOUS, INTEGER, MINIMIZE, MAXIMIZE
from cuopt.linear_programming.solver_settings import SolverSettings
```

| Task | How |
|---|---|
| LP | `vtype=CONTINUOUS` |
| MILP (schedule, assign, roster) | `vtype=INTEGER` (binary = `lb=0, ub=1`) |
| QP | same `Problem` + quadratic objective (see API skill) |

Remote solve: export `CUOPT_REMOTE_*` in the **same** shell as Python
(see `cuopt-remote-env`). Success log includes `Using remote GPU backend`.

## Verify API (run before declaring import broken)

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  python3 -c "from cuopt.linear_programming.problem import Problem, INTEGER; print(\"api_ok\")"'
```

If this prints `api_ok`, the SDK is installed — your earlier import path
was wrong, not cuOpt.

## Pre-installed smoke scripts (do not rewrite — run as-is)

| Script | Path | When |
|---|---|---|
| LP + remote gRPC | `/sandbox/smoke_lp.py` | Gate 3 (always) |
| MILP + remote gRPC | `/sandbox/smoke_milp.py` | Scheduling / assignment tasks |
| VRP REST | `/sandbox/smoke_vrp.py` | Routing tasks only |

**LP smoke:**

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  export CUOPT_REMOTE_HOST=host.openshell.internal && \
  export CUOPT_REMOTE_PORT=5001 && \
  python3 /sandbox/smoke_lp.py'
```

**MILP smoke** (same env vars):

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  export CUOPT_REMOTE_HOST=host.openshell.internal && \
  export CUOPT_REMOTE_PORT=5001 && \
  python3 /sandbox/smoke_milp.py'
```

**VRP smoke** (REST — no `CUOPT_REMOTE_*`):

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  python3 /sandbox/smoke_vrp.py'
```

## Scheduling / assignment skeleton

```python
from cuopt.linear_programming.problem import Problem, INTEGER, MINIMIZE
from cuopt.linear_programming.solver_settings import SolverSettings

p = Problem("assign")
assign = {}  # (entity, slot) -> Var
for e in entities:
    for s in slots:
        assign[e, s] = p.addVariable(
            vtype=INTEGER, lb=0, ub=1, name=f"x_{e}_{s}"
        )
# ... one-hot constraints, objective ...
settings = SolverSettings()
settings.set_parameter("time_limit", 600)  # solver ALWAYS returns within this window
p.solve(settings)
print(p.Status.name, p.ObjValue)  # Optimal, FeasibleFound, TimeLimit, etc. — all terminal
```

Full patterns: `cuopt-numerical-optimization-api-python`. **One job at a
time:** poll the same solve until `time_limit` returns — see
`cuopt-sandbox` "Long-running solves".

## Anti-pattern — wrong import → give up

> `from cuopt import milp` failed. I see `linear_programming` in the
> package but I'll pivot to a heuristic scheduler instead.

**Wrong.** MILP **is** `linear_programming.Problem` + `INTEGER`. Run the
verify command, copy the imports above, set `CUOPT_REMOTE_*`, solve with
cuOpt. A import mistake is not a solver outage.

## Related

- `cuopt-remote-env` — env vars + LP smoke test
- `cuopt-first` — gates before any schedule output
- `cuopt-numerical-optimization-api-python` — full LP/MILP/QP examples
