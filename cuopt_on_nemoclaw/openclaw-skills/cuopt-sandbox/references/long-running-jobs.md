# Long-running cuOpt jobs

**One cuOpt job at a time.** Wait for a terminal status before starting
the next solve.

## Why

Each solve holds a GPU slot on the host. Overlapping jobs queue or fail
with confusing errors. The user asked for one optimization — finish it.

## Rules

1. **Single in-flight job** — wait for terminal status before another
   `Problem.solve()` or REST submit.
2. **Set `time_limit`** — default can be long; cap for interactive work
   (e.g. 600–1800 s for MILP).
3. **Poll sequentially** — if async, poll status until terminal; one
   solve at a time is enough for comparison.
4. **Report status** — always paste `Problem.Status.name` (or REST
   equivalent) and objective when available.

## Python (gRPC)

```python
from cuopt.linear_programming.solver_settings import SolverSettings

settings = SolverSettings()
settings.set_parameter("time_limit", 600)
p.solve(settings)
print(p.Status.name, p.ObjValue)
```

If status is non-terminal after `time_limit`, report what you have and
suggest tightening the model or raising the limit — stay on cuOpt.

## REST / VRP

Submit one job; poll until completed, failed, or timeout. Wait for that
job to finish before submitting another.

## When the user wants faster iteration

- Reduce problem size for a smoke iteration, or tighten `time_limit`, rather
  than starting a parallel second job.
- Report best-so-far if the API exposes it.
- Keep using cuOpt for the real solve — slowness is a tuning problem,
  separate from infrastructure gate failures.
