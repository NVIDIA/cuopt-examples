# Python imports (sandbox)

**Use the canonical import path.** LP, MILP, and QP share one entrypoint
(there is no separate `cuopt.milp` package):

```python
from cuopt.linear_programming.problem import Problem, CONTINUOUS, INTEGER, MINIMIZE, MAXIMIZE
from cuopt.linear_programming.solver_settings import SolverSettings
```

| Task | Variable type |
|---|---|
| LP | `vtype=CONTINUOUS` |
| MILP (schedule, assign) | `vtype=INTEGER` (binary: `lb=0, ub=1`) |
| QP | same `Problem` + quadratic objective |

Full examples: vendored skill `cuopt-numerical-optimization-api-python`.

## Verify before declaring import broken

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  python3 -c "from cuopt.linear_programming.problem import Problem, INTEGER; print(\"api_ok\")"'
```

If this prints `api_ok`, the SDK works — adjust your import path and
continue with cuOpt.

## Scheduling skeleton

```python
from cuopt.linear_programming.problem import Problem, INTEGER, MINIMIZE
from cuopt.linear_programming.solver_settings import SolverSettings

p = Problem("assign")
assign = {}
for e in entities:
    for s in slots:
        assign[e, s] = p.addVariable(vtype=INTEGER, lb=0, ub=1, name=f"x_{e}_{s}")
# ... constraints, objective ...
settings = SolverSettings()
settings.set_parameter("time_limit", 600)
p.solve(settings)
print(p.Status.name, p.ObjValue)
```

Remote env vars must be set in the same shell — see
`references/remote-env-and-smoke.md`.
