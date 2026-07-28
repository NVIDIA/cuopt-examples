# Python imports (sandbox)

**Use the canonical import path.** LP, MILP, and QP share one entrypoint
(there is no separate `cuopt.milp` package):

```python
from cuopt.linear_programming.problem import Problem, CONTINUOUS, INTEGER, MINIMIZE, MAXIMIZE
from cuopt.linear_programming.solver_settings import SolverSettings

# Preferred when this import is available:
from cuopt.grpc.linear_programming import Client, GrpcError, JobStatus
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

## Scheduling skeleton (async client available)

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
client = Client("host.openshell.internal", 5001, tls=False)
job_id = client.submit(p, settings)
print(f"job_id={job_id}", flush=True)
status = client.wait(job_id, timeout=660)
print(f"job_status={status.name}")
if status == JobStatus.COMPLETED:
    names = [v.getVariableName() for v in p.getVariables()]
    solution = client.result(job_id, names)
    print(solution.get_termination_reason(), solution.get_primal_objective())
    print(solution.get_vars())
    # After results are saved/validated, delete frees server capacity.
    # delete() also cancels queued/running jobs on current nightlies.
    client.delete(job_id)
```

Full lifecycle and errors: `references/async-grpc-python.md`.
If the `Client` import fails, retain the same model-building imports and use
`references/remote-execution-fallback.md`.
